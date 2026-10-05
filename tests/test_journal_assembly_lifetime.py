"""Long connected writer execution, cancellation fences and exact-job descendants."""

import os
import sys
import time
from pathlib import Path
from threading import Event, Thread

import pytest

from tests.journal_assembly_helpers import connected, managed_process, queue_media
from tests.test_journal_assembly_faults import writer_code
from tests.owned_process_helpers import Events
from tests.capture_handoff_helpers import observations, reserve
from tikrec.assembly_types import AssemblyError
from tikrec.journal_assembly import JournalAssembly

pytestmark = pytest.mark.skipif(os.name != "nt", reason="actual Windows connected lifetime")


def launch(adapter):
    """Run the adapter on a disposable thread and retain its result or error."""
    results = []
    def run():
        try:
            results.append(adapter.run())
        except BaseException as error:
            results.append(error)
    thread = Thread(target=run)
    thread.start()
    return thread, results


@pytest.mark.parametrize("boundary", ["after_launch_intent", "native_after_create", "after_identity",
    "before_resume_fence", "native_after_resume", "after_assembly_diagnostics"])
def test_cancel_and_concurrent_close_cannot_seal_on_either_side_of_resume(connected, boundary):
    adapter, _, _, _ = connected
    runner = adapter.coordinator
    ready, release = Event(), Event()
    def fault(point):
        if point == boundary:
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
        if closer.ident is not None:
            closer.join(15)
        assert not thread.is_alive() and not closer.is_alive()
        runner._fault = lambda _: None
    assert len(results) == 1 and isinstance(results[0], AssemblyError)
    assert closed == [False] and not adapter.close()
    assert runner.journal.scratch(runner.token)["candidate"] is None
    assert runner.scratch.workspace.handle is not None
    assert len(runner.children) == 1
    if boundary not in {"native_after_resume", "after_assembly_diagnostics"}:
        assert not any(runner.scratch.path.iterdir())


def test_long_writer_exceeds_reader_bound_and_keeps_capture_available(connected, monkeypatch):
    import tikrec.assembly_launcher as launcher
    adapter, bridge, _, _ = connected
    runner, ready = adapter.coordinator, Event()
    original = launcher.CONCAT_LAUNCHER
    monkeypatch.setattr(launcher, "CONCAT_LAUNCHER", "import time;time.sleep(31.1)\n" + original)
    runner._fault = lambda point: ready.set() if point == "native_after_resume" else None
    started = time.monotonic()
    thread, results = launch(adapter)
    try:
        assert ready.wait(10)
        second, _ = queue_media(runner.authority, runner.authority.root.parent, name="second", room="234")
        contender = JournalAssembly(runner.authority, ffmpeg=adapter.ffmpeg, ffprobe=adapter.ffprobe)
        assert contender.run() is None and not contender.coordinator.children
        assert contender.close()
        captures = [reserve(runner.authority, "capture3", room="345", creator="c3"),
                    reserve(runner.authority, "capture4", room="456", creator="c4")]
        status = runner.journal.status()
        assert len(status["units"]) == 4
        assert sum(b["session"] is not None for b in status["bindings"]) == 2
        with pytest.raises(OSError):
            next(Path(bridge.intent.parts_path).glob("part-*.flv")).write_bytes(b"refused")
        data = (runner.authority.root.parent / "one-source1.flv").read_bytes()
        for capture, room in zip(captures, ("345", "456"), strict=True):
            assert capture.run(**observations(data, room=room)).phase == "queued"
        assert runner.journal.session(second.intent.session_id)["phase"] == "queued"
    finally:
        thread.join(40)
        if thread.is_alive():
            adapter.cancel()
            thread.join(10)
        assert not thread.is_alive()
    assert time.monotonic() - started >= 31
    assert len(results) == 1 and not isinstance(results[0], BaseException)
    assert results[0].state == "candidate_ready"
    assert len(runner.journal.status()["units"]) == 4 and len(runner.children) == 1


def test_unknown_job_status_retains_inputs_and_scratch(connected, monkeypatch):
    adapter, _, _, _ = connected
    runner = adapter.coordinator
    writer_code(monkeypatch, "import time;time.sleep(15)")
    def unavailable():
        raise OSError("whole-job status/termination unavailable")
    def fault(point):
        if point == "native_after_resume":
            native = runner.children[-1]["process"].native
            monkeypatch.setattr(native, "status", unavailable)
            monkeypatch.setattr(native, "terminate", unavailable)
    runner._fault = fault
    with pytest.raises(AssemblyError):
        adapter.run()
    assert not adapter.close(0) and not runner.guard.closed
    assert runner.scratch.workspace.handle is not None
    assert runner.journal.owned_attempt(runner.token)["child"]["exit"] is None
    assert runner.journal.scratch(runner.token)["candidate"] is None


def test_wrapper_exit_is_not_whole_job_exit_and_other_job_survives(connected, monkeypatch, managed_process):
    import tikrec.assembly_launcher as launcher
    adapter, _, _, _ = connected
    runner = adapter.coordinator
    with Events() as leaf, Events() as unrelated:
        code = "from tests.owned_process_probe import events,wait;" \
            "api,handles=events(" + repr(leaf.names) + ");api.SetEvent(handles[0]);wait(api,handles[1])"
        writer_code(monkeypatch, code)
        wrapped = launcher.CONCAT_LAUNCHER.replace(
            "code = subprocess.call(command, stdin=subprocess.DEVNULL, close_fds=True)",
            "subprocess.Popen(command, stdin=subprocess.DEVNULL, close_fds=True);code = 0")
        monkeypatch.setattr(launcher, "CONCAT_LAUNCHER", wrapped)
        other = managed_process()
        other.start(Path(sys._base_executable), ["-m", "tests.owned_process_probe", "leaf",
            str(runner.authority.root.parent), *unrelated.names], cwd=runner.authority.root.parent,
            before_resume=lambda identity: identity)
        unrelated.wait()
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
            assert other.poll().state == "running"
        finally:
            leaf.release()
            unrelated.release()
            thread.join(15)
            assert not thread.is_alive()
            assert other.wait(10).root_exit_code == 0
        assert isinstance(results[0], AssemblyError) and not adapter.close()
        assert runner.journal.scratch(runner.token)["candidate"] is None
