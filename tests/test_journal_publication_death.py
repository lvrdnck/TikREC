"""Real supervisor deaths distinguish preparation from observed native publication."""

import ctypes as C
import hashlib
import json
import os
import sys
from pathlib import Path

import pytest

from tests.owned_process_helpers import Events, managed_process
from tikrec.owned_process_api import H, check, kernel
from tikrec.session_journal import SessionJournal

pytestmark = pytest.mark.skipif(os.name != "nt", reason="actual Windows supervisor death")


@pytest.mark.parametrize("mode,prepared,moved,observed", [
    ("before_publication_preparation", False, False, False),
    ("prepare_publication_before_commit", False, False, False),
    ("prepare_publication_after_commit", True, False, False),
    ("after_publication_preparation", True, False, False),
    ("before_publication_fence", True, False, False),
    ("immediately_before_native", True, False, False),
    ("immediately_after_native", True, True, False),
    ("after_publication_native", True, True, False),
    ("observe_publication_before_commit", True, True, False),
    ("observe_publication_after_commit", True, True, True),
    ("after_publication_result", True, True, True),
])
def test_death_reopens_only_committed_facts_with_no_adoption(tmp_path, managed_process, mode, prepared, moved, observed):
    api = kernel()
    api.TerminateProcess.argtypes, api.TerminateProcess.restype = [H, C.c_uint32], C.c_int
    with Events() as barrier:
        supervisor = managed_process()
        supervisor.start(Path(sys._base_executable), ["-m", "tests.journal_publication_death_probe",
            mode, str(tmp_path), *barrier.names], cwd=tmp_path, before_resume=lambda value: value)
        barrier.wait()
        context = json.loads((tmp_path / "context.json").read_text())
        check(api.TerminateProcess(supervisor.native.process, 73))
        assert api.WaitForSingleObject(supervisor.native.process, 10000) == 0
        assert supervisor.wait(10).state == "confirmed_exited"
        store = SessionJournal(Path(context["path"]), context["catalog"])
        before = store.path.read_bytes()
        owner = store.owned_attempt(context["token"])
        publication = store.publication(context["token"])
        candidate = store.scratch(context["token"])["candidate"]
        assert (publication is not None) == prepared
        if prepared:
            assert (publication["evidence"] is not None) == observed
            assert publication["binding"]["candidate"] == candidate
        output = Path(context["requested_final"])
        assert output.exists() == moved
        assert (Path(context["workspace"]) / "candidate.mp4").exists() == (not moved)
        if moved:
            assert hashlib.sha256(output.read_bytes()).hexdigest() == candidate["sha256"]
            assert output.stat().st_size == candidate["size"]
        assert candidate["publication"] == "unpublished" and candidate["validation"] == "not_checked"
        assert owner["state"] == "held" and owner["child"]["cleanup"] == 1
        session = store.session(context["session"])
        assert session["phase"] == "running" and len(store.status()["units"]) == 1
        for field in ("seal", "seal_hash", "artifacts", "rooms"):
            assert session[field] == context["original"][field]
        assert {p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in context["hashes"]} == context["hashes"]
        assert store.path.read_bytes() == before
        (tmp_path / "publication-death-evidence.json").write_text(json.dumps({"mode": mode,
            "owner": owner, "publication": publication, "candidate": candidate, "hashes": context["hashes"],
            "output_present": moved, "inspection_db_unchanged": True, "pins": store.status()}, indent=2))
