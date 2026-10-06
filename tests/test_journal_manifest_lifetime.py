"""Completion cancellation fences and native lifetime evidence on the new path."""
import os
import sys
import time
from pathlib import Path
from threading import Event, Thread
import pytest
from tests.journal_manifest_helpers import completing
from tests.journal_assembly_helpers import managed_process
from tests.test_journal_assembly_lifetime import launch
from tests.journal_validation_native_helpers import native_validator
from tests.owned_process_helpers import Events
from tests.capture_handoff_helpers import reserve, observations
from tests.test_journal_manifest_faults import BOUNDARIES
from tikrec.journal_manifest import ManifestCompletionError
pytestmark = pytest.mark.skipif(os.name != "nt", reason="native Windows completion")


@pytest.mark.parametrize('boundary', BOUNDARIES)
def test_cancellation_and_concurrent_close_fence_control_writes(completing, boundary):
    adapter, _, _, _, _ = completing
    runner, ready, release = adapter.coordinator, Event(), Event()
    def fault(point):
        if point == boundary:
            ready.set()
            assert release.wait(10)
    runner._fault = fault
    worker, results = launch(adapter)
    closed = []
    closer = Thread(target=lambda: closed.append(adapter.close()))
    try:
        assert ready.wait(15)
        closer.start()
        assert runner.cancelled.wait(5)
    finally:
        release.set()
        worker.join(15)
        if closer.ident:
            closer.join(15)
    assert not worker.is_alive() and not closer.is_alive()
    assert isinstance(results[0], ManifestCompletionError) and closed == [False]
    cap = adapter.capability
    assert cap.predecessor.handle and (cap.stage is None or cap.stage.handle)
    assert runner.journal.status()['units'] and runner.guard.retained


def test_install_fence_wins_then_cancellation_prevents_result_without_replay(completing, monkeypatch):
    from tikrec import manifest_completion as module
    adapter, _, _, _, _ = completing
    runner = adapter.coordinator
    ready, release, started, done = Event(), Event(), Event(), Event()
    native = module.rename_no_replace
    def rename(*args):
        if args[2] == 'session.json':
            ready.set()
            assert release.wait(10)
        return native(*args)
    monkeypatch.setattr(module, 'rename_no_replace', rename)
    def cancel():
        started.set()
        adapter.cancel()
        done.set()
    runner._fault = lambda point: done.wait(10) if point == 'after_manifest_install' else None
    worker, results = launch(adapter)
    canceller = Thread(target=cancel)
    try:
        assert ready.wait(15)
        canceller.start()
        assert started.wait(5) and not runner.cancelled.is_set()
    finally:
        release.set()
        worker.join(15)
        if canceller.ident:
            canceller.join(15)
    assert not worker.is_alive() and not canceller.is_alive() and done.is_set()
    assert isinstance(results[0], ManifestCompletionError)
    assert adapter.capability.installed and len(runner.journal.manifest_completion(runner.token)['steps']) == 2
    assert not adapter.close()


@pytest.mark.parametrize("mode", ["diagnostic", "nonzero", "utf8", "unknown", "descendant"])
def test_new_completion_path_retains_failed_or_unknown_validator(completing, monkeypatch, mode):
    adapter, _, _, _, _ = completing
    runner = adapter.coordinator
    with Events() as barrier:
        adapter.publication.validation.assembly.ffprobe = native_validator(runner.authority.root.parent / "validator", mode, barrier.names)
        def unavailable(*_):
            raise OSError("native lifetime unavailable")
        def fault(point):
            if point == "native_after_resume" and runner.children[-1]["intent"].get("validation_index") == 1 and mode == "unknown":
                native = runner.children[-1]["process"].native
                monkeypatch.setattr(native, "status", unavailable)
                monkeypatch.setattr(native, "terminate", unavailable)
        runner._fault = fault
        worker, results = launch(adapter)
        try:
            if mode == "descendant":
                barrier.wait()
                deadline = time.monotonic() + 10
                process = runner.children[-1]["process"]
                while process.evidence().root_exit_code is None:
                    assert time.monotonic() < deadline
                    time.sleep(0.005)
                assert process.evidence().active_processes >= 1
                assert runner.journal.owned_attempt(runner.token)["child"]["exit"] is None
                adapter.cancel()
            worker.join(20)
            assert not worker.is_alive()
            assert isinstance(results[0], ManifestCompletionError)
            assert runner.journal.publication(runner.token) is None
            assert not adapter.close(0) and not runner.guard.closed
        finally:
            barrier.release()
            worker.join(15)


def test_manifest_transition_keeps_two_captures_and_unrelated_job(completing, managed_process):
    adapter, _, _, _, _ = completing
    runner, ready, release = adapter.coordinator, Event(), Event()
    def fault(point):
        if point == "after_manifest_staged_result":
            ready.set()
            assert release.wait(10)
    runner._fault = fault
    with Events() as unrelated:
        other = managed_process()
        other.start(Path(sys._base_executable), ["-m", "tests.owned_process_probe", "leaf",
            str(runner.authority.root.parent), *unrelated.names], cwd=runner.authority.root.parent,
            before_resume=lambda identity: identity)
        unrelated.wait()
        worker, results = launch(adapter)
        try:
            assert ready.wait(10)
            captures = [reserve(runner.authority, "two", room="234", creator="c2"),
                        reserve(runner.authority, "three", room="345", creator="c3")]
            assert sum(b["session"] is not None for b in runner.journal.status()["bindings"]) == 2
            data = (runner.authority.root.parent / "one-source1.flv").read_bytes()
            for capture, room in zip(captures, ("234", "345"), strict=True):
                assert capture.run(**observations(data, room=room)).phase == "queued"
            adapter.cancel()
            assert other.poll().state == "running"
        finally:
            release.set()
            unrelated.release()
            worker.join(15)
            assert not worker.is_alive()
            assert other.wait(10).root_exit_code == 0
        assert isinstance(results[0], ManifestCompletionError)
        assert len(runner.journal.status()["units"]) == 3



@pytest.mark.parametrize("failure", ["observer", "eof", "native_cleanup", "first_and_secondary"])
def test_completion_owned_validation_cleanup_fault_retains_all_owners(completing, monkeypatch, failure):
    import tikrec.journal_validation as module
    adapter, _, _, _, _ = completing
    runner = adapter.coordinator
    first = OSError("first descriptor validation failure")
    def unavailable(*_):
        raise first
    def fault(point):
        if point == "native_after_resume" and runner.children[-1]["intent"].get("access") == "candidate_validation":
            native = runner.children[-1]["process"].native
            if failure in {"native_cleanup", "first_and_secondary"}:
                monkeypatch.setattr(native, "close", lambda: (_ for _ in ()).throw(OSError("secondary native cleanup")))
            if failure == "eof":
                status = native.status
                def exited():
                    value = status()
                    if value[0] is not None and value[1] == 0:
                        native.streams.eof.clear()
                        monkeypatch.setattr(native.streams, "read", unavailable)
                    return value
                monkeypatch.setattr(native, "status", exited)
    runner._fault = fault
    if failure in {"observer", "first_and_secondary"}:
        monkeypatch.setattr(module.ValidationDiagnostics, "observe", unavailable)
    with pytest.raises(ManifestCompletionError) as caught:
        adapter.run()
    if failure in {"observer", "first_and_secondary"}:
        assert caught.value.original is first
    assert runner.journal.publication(runner.token) is None
    assert not adapter.close() and not runner.guard.closed


