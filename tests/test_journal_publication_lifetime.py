"""Connected publication cancellation, validation lifetimes and retained cleanup."""

import os
import sys
import time
from pathlib import Path
from threading import Event, Thread

import pytest

from tests.journal_publication_helpers import publishing
from tests.journal_assembly_helpers import managed_process
from tests.test_journal_assembly_lifetime import launch
from tests.journal_validation_native_helpers import native_validator
from tests.owned_process_helpers import Events
from tests.capture_handoff_helpers import reserve, observations
from tikrec.journal_publication import PublicationError

pytestmark = pytest.mark.skipif(os.name != "nt", reason="native publication lifetimes")


@pytest.mark.parametrize("boundary", ["before_publication_preparation", "after_publication_preparation",
    "before_publication_fence", "after_publication_native", "before_publication_result", "after_publication_result"])
def test_cancel_and_close_before_and_after_publication_fence(publishing, boundary):
    adapter, bridge, _, _ = publishing
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
        assert ready.wait(10)
        closer.start()
        assert runner.cancelled.wait(5)
    finally:
        release.set()
        worker.join(15)
        if closer.ident:
            closer.join(15)
        assert not worker.is_alive() and not closer.is_alive()
        runner._fault = lambda _: None
    assert isinstance(results[0], PublicationError) and closed == [False]
    assert Path(bridge.intent.output_path).exists() == (boundary in
        {"after_publication_native", "before_publication_result", "after_publication_result"})
    assert runner.scratch.artifacts["candidate.mp4"].handle is not None and not runner.guard.closed


def test_native_fence_wins_then_cancel_cannot_grant_result_or_repeat(publishing, monkeypatch):
    adapter, bridge, _, _ = publishing
    runner, ready, release, cancel_started, cancel_done = adapter.coordinator, Event(), Event(), Event(), Event()
    from tikrec import candidate_publication as module
    native = module.rename_no_replace
    def rename(*args):
        ready.set()
        assert release.wait(10)
        native(*args)
    monkeypatch.setattr(module, "rename_no_replace", rename)
    def cancel():
        cancel_started.set()
        adapter.cancel()
        cancel_done.set()
    # After rename the canceller gets its bounded acknowledgement before proof.
    runner._fault = lambda point: cancel_done.wait(10) if point == "after_publication_native" else None
    worker, results = launch(adapter)
    canceller = Thread(target=cancel)
    try:
        assert ready.wait(10)
        canceller.start()
        assert cancel_started.wait(5)
        assert not runner.cancelled.is_set()
    finally:
        release.set()
        worker.join(15)
        if canceller.ident:
            canceller.join(15)
        assert not worker.is_alive() and not canceller.is_alive()
    assert isinstance(results[0], PublicationError) and cancel_done.is_set()
    assert Path(bridge.intent.output_path).exists()
    assert runner.journal.publication(runner.token)["evidence"] is None
    assert not adapter.close()


@pytest.mark.parametrize("boundary", ["before_resume_fence", "native_after_resume"])
def test_publication_descriptor_validator_cancel_before_and_after_resume(publishing, boundary):
    adapter, _, _, _ = publishing
    runner = adapter.coordinator
    def fault(point):
        if point == boundary and runner.children and runner.children[-1]["intent"].get("access") == "candidate_validation":
            adapter.cancel()
    runner._fault = fault
    with pytest.raises(PublicationError):
        adapter.run()
    assert runner.journal.publication(runner.token) is None
    assert not adapter.close() and not runner.guard.closed


@pytest.mark.parametrize("failure", ["observer", "eof", "native_cleanup", "first_and_secondary"])
def test_descriptor_validation_fault_cannot_prepare_publication(publishing, monkeypatch, failure):
    import tikrec.journal_validation as module
    adapter, _, _, _ = publishing
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
    with pytest.raises(PublicationError) as caught:
        adapter.run()
    if failure in {"observer", "first_and_secondary"}:
        assert caught.value.original is first
    assert runner.journal.publication(runner.token) is None
    assert not adapter.close() and not runner.guard.closed


@pytest.mark.parametrize("mode", ["diagnostic", "nonzero", "utf8", "unknown", "descendant"])
def test_descriptor_validation_failure_or_unknown_lifetime_retains_ownership(publishing, monkeypatch, mode):
    adapter, _, _, _ = publishing
    runner = adapter.coordinator
    with Events() as barrier:
        adapter.validation.assembly.ffprobe = native_validator(runner.authority.root.parent / "validator", mode, barrier.names)
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
            assert isinstance(results[0], PublicationError)
            assert runner.journal.publication(runner.token) is None
            assert not adapter.close(0) and not runner.guard.closed
        finally:
            barrier.release()
            worker.join(15)


def test_publication_keeps_two_capture_bindings_and_unrelated_job(publishing, managed_process):
    adapter, _, _, _ = publishing
    runner, ready, release = adapter.coordinator, Event(), Event()
    def fault(point):
        if point == "after_publication_preparation":
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
        assert isinstance(results[0], PublicationError)
        assert len(runner.journal.status()["units"]) == 3


@pytest.mark.parametrize("corruption", ["container", "decode"])
def test_corrupted_candidate_on_new_descriptor_path_cannot_prepare(publishing, corruption):
    adapter, _, _, _ = publishing
    runner = adapter.coordinator
    def fault(point):
        if point == "after_assembly_diagnostics":
            path = runner.scratch.path / "candidate.mp4"
            data = bytearray(path.read_bytes())
            if corruption == "container":
                data[:] = b"invalid MP4 candidate"
            else:
                start = data.index(b"mdat") + 4
                size = int.from_bytes(data[start - 8:start - 4], "big") - 8
                data[start:start + size] = b"\xff" * size
            path.write_bytes(data)
    runner._fault = fault
    with pytest.raises(PublicationError):
        adapter.run()
    receipt = runner.journal.validation(runner.token)
    assert not receipt["evidence"]["report"]["passed"]
    assert receipt["evidence"]["report"]["final_output_decode"] == "failed"
    assert runner.journal.publication(runner.token) is None
    assert not adapter.close() and not runner.guard.closed
