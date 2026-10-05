"""Actual supervisor death around retained validation authority and durable commit."""

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

pytestmark = pytest.mark.skipif(os.name != "nt", reason="actual Windows validation supervisor death")


@pytest.mark.parametrize("mode,authority,launched,identity,finished,receipt", [
    ("before_validation_authority", False, False, False, False, False),
    ("begin_validation_before_commit", False, False, False, False, False),
    ("begin_validation_after_commit", True, False, False, False, False),
    ("after_validation_authority", True, False, False, False, False),
    ("after_launch_intent", True, True, False, False, False),
    ("native_after_create", True, True, False, False, False),
    ("before_resume_fence", True, True, True, False, False),
    ("native_after_resume", True, True, True, False, False),
    ("after_validation_result", True, True, True, True, False),
    ("finish_validation_before_commit", True, True, True, True, False),
    ("finish_validation_after_commit", True, True, True, True, True),
    ("after_validation_receipt", True, True, True, True, True),
])
def test_validation_death_reopens_facts_without_adoption(tmp_path, managed_process,
        mode, authority, launched, identity, finished, receipt):
    api = kernel()
    api.TerminateProcess.argtypes, api.TerminateProcess.restype = [H, C.c_uint32], C.c_int
    with Events() as barrier:
        supervisor = managed_process()
        supervisor.start(Path(sys._base_executable), ["-m", "tests.journal_validation_death_probe",
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
            validation = store.validation(context["token"])
            assert (validation is not None) == authority
            if validation is not None:
                assert (validation["evidence"] is not None) == receipt
                assert validation["binding"]["candidate"] == scratch["candidate"]
            assert scratch["state"] == "candidate_ready"
            assert scratch["candidate"]["publication"] == "unpublished"
            assert scratch["candidate"]["validation"] == "not_checked"
            current = owned["child"]
            assert (current["intent"].get("access") == "candidate_validation") == launched
            if launched:
                assert (current["identity"] is not None) == identity
                assert (current["exit"] is not None) == finished
                assert bool(current["cleanup"]) == finished
            assert owned["state"] == "held"
            session = store.session(context["session"])
            assert session["phase"] == "running" and len(store.status()["units"]) == 1
            for field in ("seal", "seal_hash", "artifacts", "rooms"):
                assert session[field] == context["original"][field]
            assert {p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in context["hashes"]} == context["hashes"]
            assert not Path(context["requested_final"]).exists()
            assert store.path.read_bytes() == db_before
            (tmp_path / "validation-death-evidence.json").write_text(json.dumps({"mode": mode,
                "owned": owned, "scratch": scratch, "validation": validation, "unchanged": True,
                "inspection_db_unchanged": True, "final_absent": True, "hashes": context["hashes"],
                "units": store.status()["units"]}, indent=2))
        finally:
            if child is not None:
                check(api.CloseHandle(child))
