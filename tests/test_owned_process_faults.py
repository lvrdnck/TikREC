"""Deterministic faults preserve primary errors, exact controls and independent cleanup."""

import ctypes as C
import os
import sys
from pathlib import Path
from threading import Event, Thread

import pytest

from tests.owned_process_helpers import Events, managed_process
from tests.test_owned_process_lifetime import launch
from tikrec.owned_process import ProcessOwnerError
from tikrec.owned_process_api import ExtendedLimits, check

pytestmark = pytest.mark.skipif(os.name != "nt", reason="Windows native faults")


def failure(error):
    """Inject the same original object so evidence must preserve its identity."""
    def raise_error(*_):
        raise error
    return raise_error


@pytest.mark.parametrize("boundary", ["before_job", "after_job", "after_limits", "after_attributes",
                                      "before_create", "after_create", "after_identity", "before_resume", "after_resume"])
def test_faults_at_each_creation_boundary(tmp_path, managed_process, boundary):
    child = managed_process()
    guard, original = child._fault, RuntimeError(boundary)
    reached = []
    def fault(name):
        guard(name)
        reached.append(name)
        if name == boundary:
            raise original
    child._fault = fault
    with pytest.raises(ProcessOwnerError) as caught:
        child.start(Path(sys._base_executable), ["-c", "print('started')"], cwd=tmp_path,
                    before_resume=lambda value: value)
    result = caught.value.evidence
    assert result.error is original
    assert result.state == ("confirmed_exited" if "after_create" in reached else "not_created")
    assert child.closed and child.native.process is None and child.native.job is None
    if "after_create" in reached:
        assert result.identity is not None and result.identity.created > 0
    if boundary != "after_resume":
        assert not result.stdout


@pytest.mark.parametrize("function", ["SetInformationJobObject", "UpdateProcThreadAttribute", "CreateProcessW"])
def test_containment_failure_never_falls_back(tmp_path, managed_process, monkeypatch, function):
    child = managed_process()
    guard, original = child._fault, OSError("containment unavailable")
    reached = []
    def fault(name):
        guard(name)
        reached.append(name)
        if name == "after_job":
            monkeypatch.setattr(child.native.api, function, failure(original))
    child._fault = fault
    with pytest.raises(ProcessOwnerError) as caught:
        child.start(Path(sys._base_executable), ["-c", "raise AssertionError('uncontrolled')"],
                    cwd=tmp_path, before_resume=lambda value: value)
    assert caught.value.original is original and caught.value.evidence.state == "not_created"
    assert "after_create" not in reached


def test_cancel_during_blocked_authorization_never_resumes(tmp_path, managed_process):
    child, entered, release = managed_process(), Event(), Event()
    errors = []
    def authorize(value):
        entered.set()
        assert release.wait(10)
        return value
    def start():
        try:
            child.start(Path(sys._base_executable), ["-c", "print('forbidden')"], cwd=tmp_path, before_resume=authorize)
        except BaseException as error:
            errors.append(error)
    thread = Thread(target=start)
    thread.start()
    try:
        assert entered.wait(10)
        assert child.cancel(5).state == "confirmed_exited"
    finally:
        release.set()
        thread.join(10)
    assert not thread.is_alive() and len(errors) == 1 and isinstance(errors[0], ProcessOwnerError)
    assert not child.evidence().stdout


@pytest.mark.parametrize("function", ["QueryInformationJobObject", "WaitForSingleObject", "GetProcessTimes",
                                      "PeekNamedPipe", "TerminateJobObject"])
def test_native_failure_is_unknown_and_retains_control(tmp_path, managed_process, monkeypatch, function):
    with Events() as barrier:
        child = managed_process()
        launch(child, tmp_path, "leaf", barrier.names)
        barrier.wait()
        handles = child.native.job, child.native.process, child.native.thread
        saved = getattr(child.native.api, function)
        error = OSError(function)
        monkeypatch.setattr(child.native.api, function, failure(error))
        result = child.cancel(0) if function == "TerminateJobObject" else child.poll()
        assert result.state == "exit_unknown" and result.error is error
        assert not child.closed and handles == (child.native.job, child.native.process, child.native.thread)
        monkeypatch.setattr(child.native.api, function, saved)
        assert child.close(5).state == "confirmed_exited"
        assert child.evidence().error is error


def test_creation_identity_corruption_retains_controls(tmp_path, managed_process):
    with Events() as barrier:
        child = managed_process()
        launch(child, tmp_path, "leaf", barrier.names)
        barrier.wait()
        saved = child.native.initial
        child.native.initial = saved[0], saved[1] + 1, saved[2]
        assert child.poll().state == "exit_unknown"
        assert child.close(0).state == "exit_unknown" and not child.closed
        child.native.initial = saved
        assert child.close(5).state == "confirmed_exited"


def test_callback_failure_and_secondary_cleanup_are_preserved(tmp_path, managed_process, monkeypatch):
    child = managed_process()
    original, secondary = ValueError("authorize failed"), OSError("close failed")
    saved = []
    def authorize(_):
        saved.append(child.native.api.CloseHandle)
        monkeypatch.setattr(child.native.api, "CloseHandle", failure(secondary))
        raise original
    with pytest.raises(ProcessOwnerError) as caught:
        child.start(Path(sys._base_executable), ["-c", "print('forbidden')"], cwd=tmp_path, before_resume=authorize)
    assert caught.value.original is original and secondary in caught.value.diagnostics
    assert caught.value.evidence.state == "confirmed_exited" and not child.closed
    monkeypatch.setattr(child.native.api, "CloseHandle", saved[0])
    assert child.close().state == "confirmed_exited" and child.closed


@pytest.mark.parametrize("function", ["CreatePipe", "CreateFileW", "SetHandleInformation", "InitializeProcThreadAttributeList"])
def test_partial_native_setup_failure_releases_created_resources(tmp_path, managed_process, monkeypatch, function):
    child = managed_process()
    guard, original = child._fault, OSError(function)
    def fault(name):
        guard(name)
        if name == "after_limits":
            monkeypatch.setattr(child.native.api, function, failure(original))
    child._fault = fault
    with pytest.raises(ProcessOwnerError) as caught:
        child.start(Path(sys._base_executable), [], cwd=tmp_path, before_resume=lambda value: value)
    assert caught.value.original is original and caught.value.evidence.state == "not_created"
    assert child.closed and not child.native.streams.child and not child.native.streams.readers


@pytest.mark.parametrize("function", ["ReadFile", "GetExitCodeProcess"])
def test_stream_and_exit_code_errors_never_supply_exit_proof(tmp_path, managed_process, monkeypatch, function):
    child = managed_process()
    child.start(Path(sys._base_executable), ["-c", "print('data')"], cwd=tmp_path, before_resume=lambda value: value)
    assert child.native.api.WaitForSingleObject(child.native.process, 10000) == 0
    saved, original = getattr(child.native.api, function), OSError(function)
    monkeypatch.setattr(child.native.api, function, failure(original))
    assert child.poll().state == "exit_unknown" and child.evidence().error is original
    assert child.close(0).state == "exit_unknown" and child.native.process is not None
    monkeypatch.setattr(child.native.api, function, saved)
    assert child.close(5).state == "confirmed_exited"


def test_attribute_cleanup_does_not_replace_creation_error(tmp_path, managed_process, monkeypatch):
    child = managed_process()
    original, secondary = RuntimeError("create failure"), RuntimeError("attribute cleanup failure")
    guard = child._fault
    def fault(name):
        guard(name)
        if name == "before_create":
            # Release native memory before raising the simulated cleanup diagnostic.
            delete = child.native.api.DeleteProcThreadAttributeList
            def cleanup(value):
                delete(value)
                raise secondary
            monkeypatch.setattr(child.native.api, "DeleteProcThreadAttributeList", cleanup)
            raise original
    child._fault = fault
    with pytest.raises(ProcessOwnerError) as caught:
        child.start(Path(sys._base_executable), [], cwd=tmp_path, before_resume=lambda value: value)
    assert caught.value.original is original and secondary in caught.value.diagnostics


def test_incompatible_parent_job_refuses_nested_creation(tmp_path, managed_process):
    with Events() as barrier:
        child = managed_process()
        def authorize(value):
            restrictions = ExtendedLimits()
            check(child.native.api.QueryInformationJobObject(child.native.job, 9, C.byref(restrictions), C.sizeof(restrictions), None))
            restrictions.basic.flags |= 8  # Parent capacity is exhausted by this disposable owner.
            restrictions.basic.active_limit = 1
            check(child.native.api.SetInformationJobObject(child.native.job, 9, C.byref(restrictions), C.sizeof(restrictions)))
            return value
        child.start(Path(sys._base_executable), ["-m", "tests.owned_process_probe", "incompatible", str(tmp_path), *barrier.names],
                    cwd=tmp_path, before_resume=authorize)
        barrier.wait()
        import json
        context = json.loads((tmp_path / "context.json").read_text())
        assert context["state"] == "not_created"
        assert child.wait(10).state == "confirmed_exited"


def test_repeated_failed_polls_bound_secondary_diagnostics(tmp_path, managed_process, monkeypatch):
    with Events() as barrier:
        child = managed_process()
        launch(child, tmp_path, "leaf", barrier.names)
        barrier.wait()
        saved = child.native.api.QueryInformationJobObject
        def fail(*_):
            raise OSError("repeated query fault")
        monkeypatch.setattr(child.native.api, "QueryInformationJobObject", fail)
        first = child.poll().error
        for _ in range(49):
            assert child.poll().state == "exit_unknown"
        result = child.evidence()
        assert result.error is first and len(result.diagnostics) == 31 and result.diagnostics_dropped == 18
        monkeypatch.setattr(child.native.api, "QueryInformationJobObject", saved)
        assert child.close(5).state == "confirmed_exited"
