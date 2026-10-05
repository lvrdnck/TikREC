"""Explicit validation lifetimes, cancellation fences and exact descendant ownership."""

import os
import time
from threading import Event, Thread

import pytest

from tests.test_journal_validation import validated, managed_process
from tests.test_journal_assembly_lifetime import launch
from tests.journal_validation_native_helpers import native_validator
from tests.owned_process_helpers import Events
from tikrec.journal_validation import ValidationError
from tests.capture_handoff_helpers import reserve, observations
from tests.journal_assembly_helpers import queue_media
from tikrec.journal_assembly import JournalAssembly

pytestmark = pytest.mark.skipif(os.name != "nt", reason="native validation lifetime")


@pytest.mark.parametrize("boundary", ["after_validation_authority", "after_launch_intent", "native_after_create",
    "after_identity", "before_resume_fence", "native_after_resume", "after_validation_result",
    "before_validation_receipt", "after_validation_receipt"])
def test_cancel_and_close_on_both_sides_of_validator_resume(validated, boundary):
    adapter, _, _, _ = validated
    runner, ready, release = adapter.coordinator, Event(), Event()
    def fault(point):
        current = runner.children[-1] if runner.children else None
        validating = current and current["intent"].get("access") == "candidate_validation"
        if point == boundary and (validating or point == "after_validation_authority"):
            ready.set()
            assert release.wait(10)
    runner._fault = fault
    thread, results = launch(adapter)
    closed = []
    closer = Thread(target=lambda: closed.append(adapter.close()))
    try:
        assert ready.wait(10)
        closer.start()
        assert runner.cancelled.wait(5)
    finally:
        release.set()
        thread.join(15)
        if closer.ident:
            closer.join(15)
        assert not thread.is_alive() and not closer.is_alive()
        runner._fault = lambda _: None
    assert len(results) == 1 and isinstance(results[0], ValidationError)
    assert closed == [False] and not runner.guard.closed
    assert runner.scratch.artifacts["candidate.mp4"].handle is not None
    receipt = runner.journal.validation(runner.token)
    if boundary != "after_validation_receipt":
        assert receipt["evidence"] is None


@pytest.mark.parametrize("mode", ["diagnostic", "nonzero", "utf8"])
def test_real_validator_failures_and_final_diagnostic_tail(validated, mode):
    adapter, _, _, _ = validated
    runner = adapter.coordinator
    adapter.assembly.ffprobe = native_validator(runner.authority.root.parent / "validator", mode)
    with pytest.raises(ValidationError):
        adapter.run()
    receipt = runner.journal.validation(runner.token)
    if mode == "utf8":
        assert receipt["evidence"] is None
    else:
        assert not receipt["evidence"]["report"]["passed"]
        decode = receipt["evidence"]["children"][1]
        assert decode["exit"]["code"] == (23 if mode == "nonzero" else 0)
        assert decode["diagnostics"]["complete"]
        if mode == "diagnostic":
            assert decode["diagnostics"]["dropped"][1] > 0
            assert decode["diagnostics"]["counts"]["stderr"] > 20000
            assert any("validation decode failed" in f["message"] for f in receipt["evidence"]["report"]["findings"])
    assert not adapter.close() and not runner.guard.closed


def test_long_validation_exceeds_reader_deadline_without_changing_generic_readers(validated):
    adapter, _, _, _ = validated
    runner = adapter.coordinator
    adapter.assembly.ffprobe = native_validator(runner.authority.root.parent / "validator", "long")
    started = time.monotonic()
    assert adapter.run()["passed"]
    assert time.monotonic() - started >= 31
    assert runner.journal.validation(runner.token)["evidence"]["report"]["passed"]


def test_unknown_validation_lifetime_retains_all_pins(validated, monkeypatch):
    adapter, _, _, _ = validated
    runner = adapter.coordinator
    with Events() as barrier:
        adapter.assembly.ffprobe = native_validator(runner.authority.root.parent / "validator", "unknown", barrier.names)
        def unavailable(*_):
            raise OSError("validation native status/termination unavailable")
        def fault(point):
            if point == "native_after_resume" and runner.children[-1]["intent"].get("validation_index") == 1:
                native = runner.children[-1]["process"].native
                monkeypatch.setattr(native, "status", unavailable)
                monkeypatch.setattr(native, "terminate", unavailable)
        runner._fault = fault
        try:
            with pytest.raises(ValidationError):
                adapter.run()
            assert not adapter.close(0) and not runner.guard.closed
            assert runner.journal.validation(runner.token)["evidence"] is None
            assert runner.journal.owned_attempt(runner.token)["child"]["exit"] is None
        finally:
            barrier.release()


def test_validator_root_exit_does_not_hide_descendant_lifetime(validated):
    adapter, _, _, _ = validated
    runner = adapter.coordinator
    with Events() as leaf:
        adapter.assembly.ffprobe = native_validator(runner.authority.root.parent / "validator", "descendant", leaf.names)
        thread, results = launch(adapter)
        try:
            leaf.wait()
            process = runner.children[-1]["process"]
            deadline = time.monotonic() + 10
            while process.evidence().root_exit_code is None:
                assert time.monotonic() < deadline
                time.sleep(0.005)
            assert process.evidence().active_processes >= 1
            assert runner.journal.owned_attempt(runner.token)["child"]["exit"] is None
            adapter.cancel()
        finally:
            leaf.release()
            thread.join(15)
            assert not thread.is_alive()
        assert isinstance(results[0], ValidationError)
        assert runner.journal.validation(runner.token)["evidence"] is None
        assert not adapter.close() and not runner.guard.closed


def test_validation_keeps_two_capture_bindings_available_and_other_jobs_untouched(validated, managed_process):
    import sys
    from pathlib import Path
    adapter, _, _, _ = validated
    runner = adapter.coordinator
    with Events() as barrier, Events() as unrelated:
        adapter.assembly.ffprobe = native_validator(runner.authority.root.parent / "validator", "barrier", barrier.names)
        other = managed_process()
        other.start(Path(sys._base_executable), ["-m", "tests.owned_process_probe", "leaf",
            str(runner.authority.root.parent), *unrelated.names], cwd=runner.authority.root.parent,
            before_resume=lambda identity: identity)
        unrelated.wait()
        thread, results = launch(adapter)
        try:
            barrier.wait()
            second, _ = queue_media(runner.authority, runner.authority.root.parent, name="second", room="234")
            contender = JournalAssembly(runner.authority, ffmpeg=adapter.assembly.ffmpeg, ffprobe=adapter.assembly.ffprobe)
            assert contender.run() is None and contender.close()
            captures = [reserve(runner.authority, "three", room="345", creator="c3"),
                        reserve(runner.authority, "four", room="456", creator="c4")]
            assert sum(b["session"] is not None for b in runner.journal.status()["bindings"]) == 2
            data = (runner.authority.root.parent / "one-source1.flv").read_bytes()
            for capture, room in zip(captures, ("345", "456"), strict=True):
                assert capture.run(**observations(data, room=room)).phase == "queued"
            adapter.cancel()
            assert other.poll().state == "running"
            assert len(runner.journal.status()["units"]) == 4
            assert runner.journal.session(second.intent.session_id)["phase"] == "queued"
        finally:
            barrier.release()
            unrelated.release()
            thread.join(15)
            assert not thread.is_alive()
            assert other.wait(10).root_exit_code == 0
        assert isinstance(results[0], ValidationError) and not adapter.close()
