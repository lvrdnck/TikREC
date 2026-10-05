"""Truthful cleanup, bounded repeat close and failure-safe secondary bookkeeping."""

import os
from threading import Thread

import pytest

from tests.attempt_scratch_helpers import scratch_runner, write_candidate, sealed, managed_process
from tikrec.attempt_coordinator import AttemptError


pytestmark = pytest.mark.skipif(os.name != "nt", reason="actual Windows scratch objects")


@pytest.mark.parametrize("secondary", ["lookup", "persistence", "advance"])
def test_secondary_hold_bookkeeping_never_replaces_first(scratch_runner, monkeypatch, secondary):
    runner = scratch_runner
    scratch = runner.reserve_scratch()
    original = ValueError("first scratch failure")
    def unavailable(*_):
        raise OSError("secondary " + secondary)
    method = {"lookup": (runner.journal, "scratch"),
              "persistence": (runner.journal, "hold_scratch"),
              "advance": (runner.guard, "advance")}[secondary]
    monkeypatch.setattr(*method, unavailable)
    for _ in range(40):
        scratch.hold(original)
    assert scratch.failure is original and runner.cancelled.is_set()
    assert runner.errors and len(runner.errors) <= 32
    if secondary == "lookup":
        assert runner.errors_dropped > 0
    assert scratch.workspace.handle is not None and not runner.close()


def test_partial_created_workspace_remains_retained_after_close(scratch_runner, monkeypatch):
    runner = scratch_runner
    original = ValueError("create acknowledgement failed")
    def fault(point):
        if point == "after_scratch_create":
            raise original
    def unavailable(_):
        raise OSError("scratch lookup unavailable")
    runner._fault = fault
    monkeypatch.setattr(runner.journal, "scratch", unavailable)
    with pytest.raises(AttemptError) as caught:
        runner.reserve_scratch()
    assert caught.value.original is original and runner.scratch.created
    assert not runner.close()
    evidence = runner.cleanup_evidence()
    assert evidence["execution_revoked"] and not evidence["cleanup_complete"]
    assert evidence["scratch"]["workspace_retained"]


@pytest.mark.parametrize("divergence", ["receipt_unavailable", "advance_failure"])
def test_durable_candidate_commit_does_not_adopt_missing_local_ack(scratch_runner, monkeypatch, divergence):
    runner = scratch_runner
    scratch, launch = write_candidate(runner)
    def lost(kind, point):
        if kind == "seal_candidate" and point == "after_commit":
            raise OSError("candidate commit acknowledgement lost")
    def unavailable(_):
        raise OSError("candidate receipt unavailable")
    advance = runner.guard.advance
    def failed_advance(result):
        if result.get("publication") == "unpublished":
            raise OSError("candidate local advance failed")
        return advance(result)
    if divergence == "receipt_unavailable":
        runner.journal._fault = lost
        monkeypatch.setattr(runner.journal, "operation", unavailable)
    else:
        monkeypatch.setattr(runner.guard, "advance", failed_advance)
    with pytest.raises(Exception):
        scratch.seal_candidate(launch)
    record = runner.journal.scratch(runner.token)
    assert record["state"] == "candidate_ready" and record["candidate"]["publication"] == "unpublished"
    assert not scratch.candidate_ready and not runner.close()
    assert scratch.workspace.handle is not None and scratch.artifacts["candidate.mp4"].handle is not None
    assert runner.cleanup_evidence()["scratch"]["candidate_ready_local"] is False


def test_concurrent_repeat_close_and_cancel_preserve_held_scratch(scratch_runner):
    runner = scratch_runner
    scratch = runner.reserve_scratch()
    assert not runner.close()
    before = runner.journal.path.read_bytes()
    results, errors = [], []
    def close():
        try:
            results.append(runner.close(1))
        except BaseException as error:
            errors.append(error)
    threads = [Thread(target=close) for _ in range(4)] + [Thread(target=runner.cancel) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(10)
        assert not thread.is_alive()
    assert not errors and results == [False] * 4
    assert scratch.workspace.handle is not None and not runner.closed
    assert runner.journal.path.read_bytes() == before


@pytest.mark.parametrize("target", ["descriptor", "workspace"])
def test_native_close_fault_retains_exact_owner_until_confirmed(scratch_runner, monkeypatch, target):
    runner = scratch_runner
    scratch, launch = write_candidate(runner)
    scratch.seal_candidate(launch)
    held = scratch.artifacts["candidate.mp4"] if target == "descriptor" else scratch.workspace
    handle, descriptor = held.handle, held.fd
    with monkeypatch.context() as patch:
        if target == "descriptor":
            native_close = os.close
            def failed_close(fd):
                if fd == descriptor:
                    raise OSError("exact descriptor close failed")
                return native_close(fd)
            patch.setattr(os, "close", failed_close)
        else:
            api = held.api
            class FaultApi:
                def __getattr__(self, name):
                    return getattr(api, name)
                def CloseHandle(self, value):
                    return 0 if value == handle else api.CloseHandle(value)
            patch.setattr(held, "api", FaultApi())
        assert not runner.close()
        assert held.handle == handle and held.fd == descriptor
        assert not runner.close() and not runner.cleanup_evidence()["cleanup_complete"]
    assert runner.close() and held.handle is None and held.fd is None
