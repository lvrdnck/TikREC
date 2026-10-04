"""Real Windows descendants, nesting, owner death, last handles and bounded waits."""

import ctypes as C
import json
import os
import sys
import time
from pathlib import Path

import pytest

from tests.owned_process_helpers import Events, duplicate, managed_process
from tikrec.owned_process_api import H, check, kernel

pytestmark = pytest.mark.skipif(os.name != "nt", reason="Windows Job Object evidence")


def launch(child, directory, mode, names):
    """Start a contained test probe with an explicit native executable and vector."""
    return child.start(Path(sys._base_executable), ["-m", "tests.owned_process_probe", mode, str(directory), *names],
                       cwd=directory, before_resume=lambda value: value)


@pytest.mark.parametrize("mode", ["before_create", "after_create", "before_resume", "running", "running_tree"])
def test_owner_death_at_native_boundaries(tmp_path, managed_process, mode):
    api = kernel()
    api.TerminateProcess.argtypes, api.TerminateProcess.restype = [H, C.c_uint32], C.c_int
    with Events() as barrier:
        owner = managed_process()
        launch(owner, tmp_path, mode, barrier.names)
        barrier.wait()
        context = json.loads((tmp_path / "context.json").read_text())
        # Duplicate only the child PROCESS object, never its kill-on-close job.
        held = [duplicate(api, value, source=owner.native.process)
                for key, value in context.items() if key in {"handle", "descendant"} and value]
        try:
            check(api.TerminateProcess(owner.native.process, 71))
            assert api.WaitForSingleObject(owner.native.process, 10000) == 0
            for handle in held:
                assert api.WaitForSingleObject(handle, 10000) == 0
            assert owner.wait(10).state == "confirmed_exited"
        finally:
            for handle in held:
                check(api.CloseHandle(handle))


def test_last_job_handle_closure_and_compatible_nesting(tmp_path, managed_process):
    api = kernel()
    with Events() as barrier:
        owner = managed_process()
        launch(owner, tmp_path, "last_handle", barrier.names)
        barrier.wait()
        context = json.loads((tmp_path / "context.json").read_text())
        held = duplicate(api, context["handle"], source=owner.native.process)
        try:
            assert api.WaitForSingleObject(held, 0) == 258
            barrier.release()
            assert api.WaitForSingleObject(held, 10000) == 0
            result = owner.wait(10)
            assert result.state == "confirmed_exited" and result.root_exit_code == 0
        finally:
            check(api.CloseHandle(held))


def test_root_exit_is_not_descendant_exit_and_unrelated_job_survives(tmp_path, managed_process):
    with Events() as leaf, Events() as root, Events() as unrelated:
        other, tree = managed_process(), managed_process()
        launch(other, tmp_path, "leaf", unrelated.names)
        unrelated.wait()
        launch(tree, tmp_path, "tree", [*leaf.names, root.names[1]])
        leaf.wait()
        root.release()
        deadline = time.monotonic() + 10
        while tree.poll().root_exit_code is None:
            assert time.monotonic() < deadline, tree.evidence()
            time.sleep(0.005)
        result = tree.evidence()
        assert result.state == "running" and result.active_processes >= 1
        assert tree.native.api.WaitForSingleObject(tree.native.process, 0) == 0
        assert tree.wait(0).state == "exit_unknown"
        for _ in range(3):
            assert tree.cancel(5).state == "confirmed_exited"
        assert other.poll().state == "running" and other.evidence().active_processes >= 1
        assert other.native.api.WaitForSingleObject(other.native.process, 0) == 258
        unrelated.release()
        assert other.wait(10).root_exit_code == 0


def test_silent_stream_wait_timeout_retains_exact_handles(tmp_path, managed_process):
    with Events() as barrier:
        child = managed_process()
        launch(child, tmp_path, "leaf", barrier.names)
        barrier.wait()
        original = (child.native.job, child.native.process, child.native.thread)
        started = time.monotonic()
        assert child.wait(0.02).state == "exit_unknown"
        assert time.monotonic() - started < 1
        assert original == (child.native.job, child.native.process, child.native.thread)
        assert child.cancel(5).state == "confirmed_exited"


def test_exit_code_259_requires_handle_signal(tmp_path, managed_process):
    child = managed_process()
    child.start(Path(sys._base_executable), ["-c", "import ctypes; ctypes.windll.kernel32.ExitProcess(259)"],
                cwd=tmp_path, before_resume=lambda value: value)
    result = child.wait(10)
    assert result.state == "confirmed_exited" and result.root_exit_code == 259
