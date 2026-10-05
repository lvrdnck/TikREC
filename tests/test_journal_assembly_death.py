"""Real supervisor termination across the NEW journal-connected media execution."""

import ctypes as C
import hashlib
import json
import os
import sys
from pathlib import Path

import pytest

from tests.owned_process_helpers import Events, duplicate, managed_process
from tikrec.owned_process_api import H, check, kernel
from tikrec.session_journal import SessionJournal

pytestmark = pytest.mark.skipif(os.name != "nt", reason="real connected supervisor death")


@pytest.mark.parametrize("mode,state,created,identity,executed,bound,candidate", [
    ("after_media_plan", None, False, False, False, False, False),
    ("reserve_scratch_after_commit", "reserved", False, False, False, False, False),
    ("after_scratch_create", "reserved", True, False, False, False, False),
    ("after_launch_intent", "bound", True, False, False, False, False),
    ("native_after_create", "bound", True, False, False, False, False),
    ("before_resume_fence", "bound", True, True, False, False, False),
    ("native_after_resume", "bound", True, True, False, False, False),
    ("after_assembly_diagnostics", "bound", True, True, True, False, False),
    ("bind_scratch_artifacts_after_commit", "bound", True, True, True, True, False),
    ("seal_candidate_before_commit", "bound", True, True, True, True, False),
    ("seal_candidate_after_commit", "candidate_ready", True, True, True, True, True),
    ("after_candidate_ready", "candidate_ready", True, True, True, True, True),
])
def test_connected_death_reopen_only_committed_facts(tmp_path, managed_process,
                                                   mode, state, created, identity, executed, bound, candidate):
    api = kernel()
    api.TerminateProcess.argtypes, api.TerminateProcess.restype = [H, C.c_uint32], C.c_int
    with Events() as barrier:
        supervisor = managed_process()
        supervisor.start(Path(sys._base_executable), ["-m", "tests.journal_assembly_death_probe",
            mode, str(tmp_path), *barrier.names], cwd=tmp_path, before_resume=lambda value: value)
        barrier.wait()
        context = json.loads((tmp_path / "context.json").read_text())
        child = duplicate(api, context["handle"], source=supervisor.native.process) if context["handle"] else None
        try:
            check(api.TerminateProcess(supervisor.native.process, 73))
            assert api.WaitForSingleObject(supervisor.native.process, 10000) == 0
            if child is not None:
                assert api.WaitForSingleObject(child, 10000) == 0
            assert supervisor.wait(10).state == "confirmed_exited"
            store = SessionJournal(Path(context["path"]), context["catalog"])
            db_before = store.path.read_bytes()
            owned, scratch = store.owned_attempt(context["token"]), store.scratch(context["token"])
            assert owned["state"] == "held"
            assert (scratch is not None) == (state is not None)
            assert Path(context["workspace"]).exists() == created
            if scratch is not None:
                assert scratch["state"] == state
                assert (scratch["candidate"] is not None) == candidate
                assert all((a["identity"] is not None) == bound for a in scratch["artifacts"])
            launch = owned["child"]
            if launch is not None:
                assert (launch["identity"] is not None) == identity
                assert (launch["exit"] is not None) == executed
                assert bool(launch["cleanup"]) == executed
                if executed:
                    assert launch["exit"]["code"] == 0 and launch["exit"]["active"] == 0
                    assert launch["diagnostics"]["complete"]
                    assert (Path(context["workspace"]) / "candidate.mp4").stat().st_size > 0
                    assert (Path(context["workspace"]) / "concat.ffconcat").stat().st_size > 0
            session = store.session(context["session"])
            assert session["phase"] == "running"
            for field in ("seal", "seal_hash", "artifacts", "rooms"):
                assert session[field] == context["original"][field]
            assert len(store.status()["units"]) == 1
            assert store.path.read_bytes() == db_before
            assert {p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in context["original_hashes"]} \
                == context["original_hashes"]
            assert {p: Path(p).read_bytes().hex() for p in context["sources"]} == context["sources"]
            assert not Path(context["requested_final"]).exists()
            if candidate:
                assert scratch["candidate"]["validation"] == "not_checked"
                assert scratch["candidate"]["publication"] == "unpublished"
            (tmp_path / "connected-death-evidence.json").write_text(json.dumps({"mode": mode,
                "owned": owned, "scratch": scratch, "units": store.status()["units"],
                "original_hashes": context["original_hashes"], "unchanged": True,
                "inspection_db_unchanged": True, "final_absent": True}, indent=2))
        finally:
            if child is not None:
                check(api.CloseHandle(child))
