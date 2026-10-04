"""Process death before/after native close + H preserves exactly one old owner."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests.capture_handoff_helpers import local_media
from tikrec.capture_handoff_authority import CaptureAuthority
from tikrec.session_journal import SessionJournal

pytestmark = pytest.mark.skipif(os.name != "nt", reason="requires native Windows process-death proof")


@pytest.mark.parametrize("boundary", ["after_marker", "after_seal", "after_queue_entry", "after_task",
                                      "after_transfer", "after_release", "before_commit", "after_commit",
                                      "confirmed_h", "after_slot_reuse", "empty_after_seal",
                                      "empty_after_release", "empty_after_commit"])
def test_process_death_preserves_capture_or_queued_owner_without_false_completion(tmp_path, boundary):
    fixture = tmp_path / "fixture.flv"
    local_media(fixture)
    root = tmp_path / "child"
    root.mkdir()
    result = subprocess.run([sys.executable, "-m", "tests.capture_handoff_crash_child",
                             str(root), str(fixture), boundary], capture_output=True, text=True, timeout=30)
    assert result.returncode == 73, result.stdout + result.stderr
    context = json.loads((root / "context.json").read_text())
    store = SessionJournal(root / "state/sessions.sqlite3", context["catalog"])
    with CaptureAuthority(store, root / "media") as owner:
        row = store.session(context["old"])
        committed = boundary in {"after_commit", "confirmed_h", "after_slot_reuse", "empty_after_commit"}
        empty = boundary.startswith("empty_")
        assert row["phase"] == (("no_assembly" if empty else "queued") if committed else "closing")
        assert bool(row["task"]) == (committed and not empty) and bool(row["seal"]) == committed
        assert owner.inspect(context["old"])["source_resume_allowed"] is False
        status = store.status()
        old_bindings = [b for b in status["bindings"] if b["session"] == context["old"]]
        old_tasks = [t for t in status["tasks"] if t["session"] == context["old"]]
        evidence = [u for u in status["units"] if u["kind"] == "evidence" and u["session"] == context["old"]]
        assert len(old_bindings) + len(old_tasks) + len(evidence) == 1
        assert len(status["units"]) == (2 if boundary == "after_slot_reuse" else 1)
        values = json.loads(Path(row["intent"]["parts_path"], "session.json").read_text())
        assert values["finalization"]["status"] == "pending"
        assert not Path(row["intent"]["output_path"]).exists()
        if boundary == "after_slot_reuse":
            newer = store.history()[1]
            assert newer["phase"] == "capturing" and newer["generation"] == row["generation"] + 1
            assert any(b["session"] == newer["id"] for b in status["bindings"])
            assert store.session(newer["id"])["intent"]["raw_copy"] is False
            assert row["intent"]["raw_copy"] is True and old_tasks[0]["state"] == "queued"
