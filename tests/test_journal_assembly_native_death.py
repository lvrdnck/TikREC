"""Exact writer and descendant termination propagate through the connected owner."""

import ctypes as C
import json
import os
import time

import pytest

from tests.journal_assembly_helpers import connected, managed_process
from tests.test_journal_assembly_faults import writer_code
from tests.test_journal_assembly_lifetime import launch
from tests.owned_process_helpers import Events, duplicate
from tikrec.owned_process_api import H, check, kernel
from tikrec.assembly_types import AssemblyError

pytestmark = pytest.mark.skipif(os.name != "nt", reason="actual connected native termination")


@pytest.mark.parametrize("target", ["writer", "descendant"])
def test_exact_native_writer_or_descendant_death_never_seals(connected, monkeypatch, target):
    import tikrec.assembly_launcher as launcher
    adapter, _, _, _ = connected
    runner, api = adapter.coordinator, kernel()
    api.TerminateProcess.argtypes, api.TerminateProcess.restype = [H, C.c_uint32], C.c_int
    with Events() as leaf:
        code = "from tests.owned_process_probe import events,wait;" \
            "api,handles=events(" + repr(leaf.names) + ");api.SetEvent(handles[0]);wait(api,handles[1])"
        writer_code(monkeypatch, code)
        wrapped = launcher.CONCAT_LAUNCHER.replace(
            "code = subprocess.call(command, stdin=subprocess.DEVNULL, close_fds=True)",
            "child = subprocess.Popen(command, stdin=subprocess.DEVNULL, close_fds=True);"
            "print(json.dumps({'handle': int(child._handle)}), flush=True);code = child.wait()")
        monkeypatch.setattr(launcher, "CONCAT_LAUNCHER", wrapped)
        thread, results = launch(adapter)
        descendant = None
        try:
            leaf.wait()
            process = runner.children[-1]["process"]
            deadline = time.monotonic() + 10
            while not process.evidence().stdout:
                assert time.monotonic() < deadline
                time.sleep(0.005)
            native_handle = json.loads(process.evidence().stdout)["handle"]
            descendant = duplicate(api, native_handle, source=process.native.process)
            victim = process.native.process if target == "writer" else descendant
            check(api.TerminateProcess(victim, 83))
            assert api.WaitForSingleObject(victim, 10000) == 0
            if target == "writer":
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
            if thread.is_alive():
                adapter.cancel()
                thread.join(10)
            assert not thread.is_alive()
            if descendant is not None:
                assert api.WaitForSingleObject(descendant, 10000) == 0
                check(api.CloseHandle(descendant))
        assert isinstance(results[0], AssemblyError) and not adapter.close()
        child = runner.journal.owned_attempt(runner.token)["child"]
        assert child["exit"]["state"] == "confirmed_exited" and child["exit"]["active"] == 0
        assert child["exit"]["code"] == 83 and child["cleanup"] == 1
        assert runner.journal.scratch(runner.token)["candidate"] is None
