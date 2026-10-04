"""R6–R7 real Windows barriers with independent exact-job cleanup on every failure."""

import os
import sys
import time
from pathlib import Path
from threading import Barrier, Event, Thread

import pytest

from tests.owned_process_helpers import Events, duplicate, managed_process
from tikrec.owned_process import ProcessOwnerError
from tikrec.owned_process_api import check, kernel

pytestmark = pytest.mark.skipif(os.name != "nt", reason="native Windows R6/R7 regression evidence")


def test_close_wins_validation_gap_without_payload_or_hidden_controls(tmp_path, managed_process, monkeypatch):
    child = managed_process()
    executable, payload = Path(sys._base_executable), tmp_path / "forbidden.txt"
    entered, release, errors = Event(), Event(), []
    original = Path.is_file
    def validation(path):
        if path == executable:
            entered.set()
            assert release.wait(10)
        return original(path)
    monkeypatch.setattr(Path, "is_file", validation)
    def start():
        try:
            child.start(executable, ["-c", f"open({str(payload)!r},'w').write('executed')"],
                        cwd=tmp_path, before_resume=lambda value: value)
        except BaseException as error:
            errors.append(error)
    thread = Thread(target=start)
    thread.start()
    try:
        assert entered.wait(10)
        assert child.close(0).state == "not_created" and child.closed
    finally:
        release.set()
        thread.join(10)
    assert not thread.is_alive()
    if child.native is not None and child.native.process is not None:
        # Baseline observation waits on the exact object, never PID disappearance.
        assert child.native.api.WaitForSingleObject(child.native.process, 10000) == 0
    assert not payload.exists()
    assert len(errors) == 1 and isinstance(errors[0], ProcessOwnerError)
    assert child.native is None and child.evidence().state == "not_created"


@pytest.mark.parametrize("stream", ["stdout", "stderr", "both"])
def test_real_tail_between_collection_and_exit_observation(tmp_path, managed_process, stream):
    with Events() as barrier:
        child = managed_process(diagnostic_limit=101)
        writes = ("os.write(1,b'O'*3037);" if stream in {"stdout", "both"} else "")
        writes += ("os.write(2,b'E'*3037);" if stream in {"stderr", "both"} else "")
        script = ("import os; from tests.owned_process_probe import events,wait; "
                  f"a,b=events({barrier.names!r}); a.SetEvent(b[0]); wait(a,b[1]); " + writes)
        child.start(Path(sys._base_executable), ["-c", script], cwd=tmp_path, before_resume=lambda value: value)
        barrier.wait()
        status, fired = child.native.status, []
        def exit_boundary():
            if not fired:
                fired.append(True)
                barrier.release()
                assert child.native.api.WaitForSingleObject(child.native.process, 10000) == 0
            deadline = time.monotonic() + 10
            while True:
                code, active = status()
                if code is not None and active == 0:
                    return code, active
                assert time.monotonic() < deadline
                time.sleep(0.005)
        child.native.status = exit_boundary
        seen = []
        result = child.poll(observer=lambda name, chunk: seen.append((name, chunk)))
        assert result.state == "confirmed_exited" and result.root_exit_code == 0 and result.active_processes == 0
        assert result.stdout == (b"O" * 101 if stream in {"stdout", "both"} else b"")
        assert result.stderr == (b"E" * 101 if stream in {"stderr", "both"} else b"")
        assert result.truncated == (2936 if stream in {"stdout", "both"} else 0, 2936 if stream in {"stderr", "both"} else 0)
        assert result.stream_status == ("complete", "complete")
        assert child.wait(0).stream_status == ("complete", "complete")
        child.poll(observer=lambda name, chunk: seen.append((name, chunk)))
        child.close(0)
        assert sum(len(chunk) for name, chunk in seen if name == "stdout") == (3037 if stream in {"stdout", "both"} else 0)
        assert sum(len(chunk) for name, chunk in seen if name == "stderr") == (3037 if stream in {"stderr", "both"} else 0)


@pytest.mark.parametrize("boundary", ["before_create", "authorization"])
def test_creation_wins_then_concurrent_cleanup_prevents_resume(tmp_path, managed_process, boundary):
    child, reached, release = managed_process(), Event(), Event()
    authorized, permit, errors, outcomes = Event(), Event(), [], []
    guard, payload = child._fault, tmp_path / "forbidden.txt"
    def fault(name):
        guard(name)
        if boundary == "before_create" and name == "before_create":
            reached.set()
            assert release.wait(10)
    def authorize(value):
        authorized.set()
        assert permit.wait(10)
        return value
    child._fault = fault
    def start():
        try:
            child.start(Path(sys._base_executable), ["-c", f"open({str(payload)!r},'w').write('bad')"],
                        cwd=tmp_path, before_resume=authorize)
        except BaseException as error:
            errors.append(error)
    thread = Thread(target=start)
    thread.start()
    cleanup = []
    ready = Barrier(4)
    def close(action):
        ready.wait(10)
        outcomes.append(getattr(child, action)(5))
    try:
        assert (reached if boundary == "before_create" else authorized).wait(10)
        cleanup = [Thread(target=close, args=(action,)) for action in ("close", "cancel", "close")]
        for worker in cleanup:
            worker.start()
        ready.wait(10)
        release.set()
        assert authorized.wait(10)
        for worker in cleanup:
            worker.join(10)
            assert not worker.is_alive()
        assert len(outcomes) == 3 and all(value.state == "confirmed_exited" for value in outcomes)
    finally:
        release.set()
        permit.set()
        thread.join(10)
        for worker in cleanup:
            worker.join(10)
    assert not thread.is_alive() and len(errors) == 1 and isinstance(errors[0], ProcessOwnerError)
    assert not payload.exists() and child.closed and child.native.process is None and child.native.job is None


def test_resume_wins_then_close_cleans_live_exact_controls(tmp_path, managed_process):
    with Events() as barrier:
        child, reached, release, attempted = managed_process(), Event(), Event(), Event()
        guard, errors, results = child._fault, [], []
        def fault(name):
            guard(name)
            if name == "after_resume":
                reached.set()
                assert release.wait(10)
        child._fault = fault
        def start():
            try:
                child.start(Path(sys._base_executable), ["-m", "tests.owned_process_probe", "leaf", str(tmp_path), *barrier.names],
                            cwd=tmp_path, before_resume=lambda value: value)
            except BaseException as error:
                errors.append(error)
        def close():
            attempted.set()
            results.append(child.close(5))
        starter = Thread(target=start)
        starter.start()
        closer = Thread(target=close)
        try:
            assert reached.wait(10)
            barrier.wait()  # Native child execution wins before close obtains the lock.
            closer.start()
            assert attempted.wait(10)
        finally:
            release.set()
            starter.join(10)
            if closer.ident is not None:
                closer.join(10)
        assert not starter.is_alive() and not closer.is_alive() and not errors
        assert results[0].state == "confirmed_exited" and child.closed
        assert child.native.process is None and child.native.job is None


def test_native_eof_timeout_keeps_proved_exit_then_reconciles(tmp_path, managed_process):
    child, api, writers = managed_process(), kernel(), []
    guard = child._fault
    def fault(name):
        guard(name)
        if name == "before_create":
            # An independently held parent writer deterministically postpones EOF.
            writers.append(duplicate(api, child.native.streams.child[1]))
    child._fault = fault
    try:
        child.start(Path(sys._base_executable), ["-c", "print('tail')"], cwd=tmp_path, before_resume=lambda value: value)
        assert api.WaitForSingleObject(child.native.process, 10000) == 0
        deadline = time.monotonic() + 10
        while child.native.status()[1] != 0:
            assert time.monotonic() < deadline
            time.sleep(0.005)
        begun = time.monotonic()
        result = child.wait(0.05)
        assert result.state == "confirmed_exited" and result.root_exit_code == 0 and result.active_processes == 0
        assert result.stream_status == ("incomplete", "complete") and isinstance(result.error, TimeoutError)
        assert time.monotonic() - begun < 1 and not child.closed and "stdout" in child.native.streams.readers
        check(api.CloseHandle(writers.pop()))
        result = child.wait(1)
        assert result.stream_status == ("complete", "complete") and result.stdout == b"tail\r\n"
        assert child.close(0).state == "confirmed_exited"
    finally:
        for writer in writers:
            check(api.CloseHandle(writer))


def test_native_final_drain_read_failure_preserves_proof_and_retryable_tail(tmp_path, managed_process, monkeypatch):
    with Events() as barrier:
        child, original = managed_process(), OSError("post-exit ReadFile fault")
        script = ("import os; from tests.owned_process_probe import events,wait; "
                  f"a,b=events({barrier.names!r}); a.SetEvent(b[0]); wait(a,b[1]); os.write(2,b'final-error')")
        child.start(Path(sys._base_executable), ["-c", script], cwd=tmp_path, before_resume=lambda value: value)
        barrier.wait()
        status, read = child.native.status, child.native.api.ReadFile
        def fail(*_):
            raise original
        def boundary():
            barrier.release()
            assert child.native.api.WaitForSingleObject(child.native.process, 10000) == 0
            deadline = time.monotonic() + 10
            while True:
                code, active = status()
                if code is not None and active == 0:
                    monkeypatch.setattr(child.native.api, "ReadFile", fail)
                    return code, active
                assert time.monotonic() < deadline
                time.sleep(0.005)
        child.native.status = boundary
        result = child.poll()
        assert result.state == "confirmed_exited" and result.error is original
        assert result.stream_status == ("complete", "incomplete") and not child.closed
        monkeypatch.setattr(child.native.api, "ReadFile", read)
        result = child.wait(1)
        assert result.state == "confirmed_exited" and result.stderr == b"final-error"
        assert result.stream_status == ("complete", "complete") and result.error is original
