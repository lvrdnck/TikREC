"""Real owner death and reopen without adoption, absence inference or retry."""

import os
import ctypes as C
import json
import sys
from pathlib import Path

import pytest

from tests.owned_process_helpers import Events, duplicate, managed_process
from tikrec.owned_process_api import H, check, kernel
from tikrec.session_journal import SessionJournal


pytestmark = pytest.mark.skipif(os.name != "nt", reason="real Windows capture and native input proof")


@pytest.mark.parametrize("mode,sequence,identity,exited", [
    ("claim_owned_after_writes", None, False, False),
    ("after_claim", 0, False, False),
    ("launch_intent_before_commit", 0, False, False),
    ("after_launch_intent", 1, False, False),
    ("native_after_create", 1, False, False),
    ("child_identity_before_commit", 1, False, False),
    ("after_identity", 1, True, False),
    ("native_after_resume", 1, True, False),
    ("child_exit_before_commit", 1, True, False),
    ("after_exit_record", 1, True, True),
])
def test_owner_death_preserves_declared_records_only(tmp_path, managed_process, mode, sequence, identity, exited):
    api = kernel()
    api.TerminateProcess.argtypes, api.TerminateProcess.restype = [H, C.c_uint32], C.c_int
    with Events() as barrier:
        supervisor = managed_process()
        supervisor.start(Path(sys._base_executable), ["-m", "tests.attempt_death_probe", mode,
            str(tmp_path), *barrier.names], cwd=tmp_path, before_resume=lambda value: value)
        barrier.wait()
        context = json.loads((tmp_path / "context.json").read_text())
        # Keep only the exact child PROCESS object. A duplicated private job would
        # prevent kill-on-last-handle-close and invalidate the death evidence.
        child = duplicate(api, context["handle"], source=supervisor.native.process) if context["handle"] else None
        try:
            check(api.TerminateProcess(supervisor.native.process, 73))
            assert api.WaitForSingleObject(supervisor.native.process, 10000) == 0
            if child is not None:
                assert api.WaitForSingleObject(child, 10000) == 0
            assert supervisor.wait(10).state == "confirmed_exited"
            store = SessionJournal(Path(context["path"]), context["catalog"])
            row = store.owned_attempt(context["token"])
            if sequence is None:
                assert row is None and store.session(context["session"])["phase"] == "queued"
            else:
                assert row["sequence"] == sequence and row["state"] == "held"
                if sequence:
                    assert (row["child"]["identity"] is not None) is identity
                    assert (row["child"]["exit"] is not None) is exited
                    assert row["child"]["cleanup"] == 0
                    assert len(store.child_history(context["token"])) == 1
                assert store.claim_next("ec82f3a1-5c02-484d-a272-e8e043f877dd",
                                        "e958c79b-d239-4e6a-8843-10fbd48a8df9") is None
                assert store.session(context["session"])["phase"] == "running"
            assert len(store.status()["units"]) == 1
            assert not (tmp_path / "media" / "one.mp4").exists()
        finally:
            if child is not None:
                check(api.CloseHandle(child))
