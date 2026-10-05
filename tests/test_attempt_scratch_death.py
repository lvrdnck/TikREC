"""Actual supervisor death establishes committed facts, not power-loss durability."""

import ctypes as C
import hashlib
import json
import os
import sys
from pathlib import Path
from uuid import uuid4

import pytest

from tests.owned_process_helpers import Events, duplicate, managed_process
from tikrec.owned_process_api import H, check, kernel
from tikrec.session_journal import SessionJournal


pytestmark = pytest.mark.skipif(os.name != "nt", reason="actual Windows supervisor death")


@pytest.mark.parametrize("mode,state,created,bound,candidate", [
    ("reserve_scratch_after_writes", None, False, False, False),
    ("reserve_scratch_after_commit", "reserved", False, False, False),
    ("after_scratch_intent", "reserved", False, False, False),
    ("after_scratch_create", "reserved", True, False, False),
    ("bind_scratch_before_commit", "reserved", True, False, False),
    ("bind_scratch_after_commit", "bound", True, False, False),
    ("after_scratch_bind", "bound", True, False, False),
    ("bind_scratch_artifacts_before_commit", "bound", True, False, False),
    ("bind_scratch_artifacts_after_commit", "bound", True, True, False),
    ("after_artifact_bind", "bound", True, True, False),
    ("seal_candidate_before_commit", "bound", True, True, False),
    ("seal_candidate_after_commit", "candidate_ready", True, True, True),
    ("after_candidate_ready", "candidate_ready", True, True, True),
])
def test_supervisor_death_never_adopts_or_infers_scratch_outcome(tmp_path, managed_process,
                                                              mode, state, created, bound, candidate):
    api = kernel()
    api.TerminateProcess.argtypes, api.TerminateProcess.restype = [H, C.c_uint32], C.c_int
    with Events() as barrier:
        supervisor = managed_process()
        supervisor.start(Path(sys._base_executable), ["-m", "tests.attempt_scratch_death_probe",
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
            row = store.owned_attempt(context["token"])
            scratch = store.scratch(context["token"])
            assert (scratch is not None) == (state is not None)
            assert Path(context["workspace"]).exists() == created
            if scratch is not None:
                assert scratch["state"] == state and (scratch["candidate"] is not None) == candidate
                assert all((item["identity"] is not None) == bound for item in scratch["artifacts"])
                if candidate:
                    assert scratch["candidate"]["publication"] == "unpublished"
                    assert scratch["candidate"]["validation"] == "not_checked"
            assert row["state"] == "held" and row["sequence"] in {0, 1}
            assert len(store.status()["units"]) == 1
            assert store.claim_next(str(uuid4()), str(uuid4())) is None
            session = store.session(context["session"])
            assert session["phase"] == "running"
            for field in ("seal", "seal_hash", "artifacts", "rooms"):
                assert session[field] == context["original"][field]
            assert {name: hashlib.sha256(Path(name).read_bytes()).hexdigest()
                    for name in context["original_hashes"]} == context["original_hashes"]
            assert not (tmp_path / "media" / "one.mp4").exists()
            (tmp_path / "death-inspection.json").write_text(json.dumps({"mode": mode,
                "owned": row, "scratch": scratch, "original_hashes_unchanged": True}, indent=2))
        finally:
            if child is not None:
                check(api.CloseHandle(child))
