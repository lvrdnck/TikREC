"""Native scratch writer cancellation, descendants, uncertain exit and cleanup faults."""

import os
import sys
import time
from pathlib import Path
from threading import Event, Thread

import pytest

from tests.attempt_scratch_helpers import scratch_runner, sealed, managed_process
from tests.owned_process_helpers import Events
from tikrec.attempt_coordinator import AttemptError


pytestmark = pytest.mark.skipif(os.name != "nt", reason="actual Windows writer lifecycle")


@pytest.mark.parametrize("boundary", ["after_launch_intent", "native_after_create", "after_identity",
                                     "before_resume_fence", "native_after_resume"])
def test_scratch_writer_cancel_and_close_on_both_sides_of_resume(scratch_runner, boundary):
    runner = scratch_runner
    scratch = runner.reserve_scratch()
    ready, release = Event(), Event()
    errors, cleanup = [], []
    def fault(point):
        if point == boundary:
            ready.set()
            assert release.wait(10), "writer barrier expired"
    runner._fault = fault
    def writer():
        try:
            scratch.run_writer(Path(sys._base_executable), ["-c",
                "from pathlib import Path;Path('candidate.mp4').write_bytes(b'candidate')"], timeout=10)
        except BaseException as error:
            errors.append(error)
    launch = Thread(target=writer)
    close = Thread(target=lambda: cleanup.append(runner.close(5)))
    launch.start()
    try:
        assert ready.wait(10)
        close.start()
        assert runner.cancelled.wait(5)
    finally:
        release.set()
        launch.join(15)
        if close.ident is not None:
            close.join(15)
        assert not launch.is_alive() and not close.is_alive()
        runner._fault = lambda _: None
    assert cleanup == [False] and not runner.closed
    assert scratch.workspace.handle is not None
    if boundary != "native_after_resume":
        assert not (scratch.path / "candidate.mp4").exists()
    assert runner.journal.scratch(runner.token)["state"] == "held"
    assert runner.journal.scratch(runner.token)["candidate"] is None
    assert len(runner.children) == 1 and runner.children[0]["process"].closed
    assert all(isinstance(error, AttemptError) for error in errors)


def test_scratch_writer_root_exit_waits_for_descendant_and_preserves_other_job(scratch_runner, managed_process):
    runner = scratch_runner
    scratch = runner.reserve_scratch()
    errors = []
    with Events() as leaf, Events() as root, Events() as unrelated:
        other = managed_process()
        other.start(Path(sys._base_executable), ["-m", "tests.owned_process_probe", "leaf",
            str(runner.authority.root.parent), *unrelated.names], cwd=runner.authority.root.parent,
            before_resume=lambda value: value)
        unrelated.wait()
        code = "from pathlib import Path;import subprocess,sys;" \
               "from tests.owned_process_probe import events,wait;" \
               "Path('candidate.mp4').write_bytes(b'candidate');" \
               "subprocess.Popen([sys._base_executable,'-m','tests.owned_process_probe','leaf'," + \
               repr(str(scratch.path)) + ",*" + repr(leaf.names) + "],close_fds=True);" + \
               "api,handles=events(" + repr(root.names) + ");wait(api,handles[1])"
        def writer():
            try:
                scratch.run_writer(Path(sys._base_executable), ["-c", code], timeout=15)
            except BaseException as error:
                errors.append(error)
        thread = Thread(target=writer)
        thread.start()
        try:
            leaf.wait()
            root.release()
            process = runner.children[0]["process"]
            deadline = time.monotonic() + 10
            while process.evidence().root_exit_code is None:
                assert time.monotonic() < deadline
                time.sleep(0.005)
            assert process.evidence().active_processes >= 1
            assert runner.journal.owned_attempt(runner.token)["child"]["exit"] is None
            runner.cancel(5)
            assert other.poll().state == "running"
        finally:
            leaf.release()
            root.release()
            unrelated.release()
            thread.join(20)
            assert not thread.is_alive()
            assert other.wait(10).root_exit_code == 0
        assert not runner.close()
        child = runner.journal.owned_attempt(runner.token)["child"]
        assert child["exit"]["active"] == 0 and child["cleanup"] == 1
        assert runner.journal.scratch(runner.token)["candidate"] is None


def test_unavailable_whole_job_status_retains_scratch_and_inputs(scratch_runner, monkeypatch):
    runner = scratch_runner
    scratch = runner.reserve_scratch()
    def fault(point):
        if point == "native_after_resume":
            native = runner.children[-1]["process"].native
            def unavailable():
                raise OSError("whole-job status unavailable")
            monkeypatch.setattr(native, "status", unavailable)
            monkeypatch.setattr(native, "terminate", unavailable)
    runner._fault = fault
    with pytest.raises(AttemptError):
        scratch.run_writer(Path(sys._base_executable), ["-c", "import time;time.sleep(15)"], timeout=0)
    assert not runner.close(0) and not runner.guard.closed
    assert scratch.workspace.handle is not None
    assert runner.journal.owned_attempt(runner.token)["child"]["exit"] is None
    with pytest.raises(AttemptError):
        runner.run_writer_child(Path(sys._base_executable), ["-c", "pass"], cwd=scratch.path,
                                phase="writer", timeout=0)
    assert len(runner.children) == 1


@pytest.mark.parametrize("failure", ["observer", "pipe", "native_cleanup"])
def test_scratch_writer_diagnostics_and_cleanup_gate_candidate(scratch_runner, monkeypatch, failure):
    runner = scratch_runner
    scratch = runner.reserve_scratch()
    def fault(point):
        if point == "native_after_resume" and failure != "observer":
            native = runner.children[-1]["process"].native
            def unavailable(*_):
                raise OSError("disposable " + failure + " fault")
            if failure == "pipe":
                status = native.status
                def exited_status():
                    value = status()
                    if value[0] is not None and value[1] == 0:
                        # Fail final EOF reconciliation only after actual
                        # whole-job status has established native exit.
                        native.streams.eof.clear()
                        monkeypatch.setattr(native.streams, "read", unavailable)
                    return value
                monkeypatch.setattr(native, "status", exited_status)
            else:
                monkeypatch.setattr(native, "close", unavailable)
    def observer(*_):
        raise ValueError("diagnostic observer failed")
    runner._fault = fault
    with pytest.raises(AttemptError):
        runner.run_writer_child(Path(sys._base_executable), ["-c",
            "from pathlib import Path;Path('candidate.mp4').write_bytes(b'candidate');print('tail')"],
            cwd=scratch.path, phase="writer", timeout=5, observer=observer if failure == "observer" else None)
    child = runner.journal.owned_attempt(runner.token)["child"]
    assert child["exit"]["state"] == "confirmed_exited"
    assert not child["diagnostics"]["complete"]
    assert not runner.close(0)
    if failure == "native_cleanup":
        assert child["cleanup"] == 0 and not runner.guard.closed
    assert scratch.workspace.handle is not None and runner.journal.scratch(runner.token)["candidate"] is None
