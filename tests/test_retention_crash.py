"""Native process death keeps handle-removal histories truthful and nonresumable."""

import os
import subprocess
import sys

import pytest

from tests.test_retention_execute import events
from tests.test_retention_plan import NOW, inspect
from tikrec.configuration import ConfigurationStore
from tikrec.retention_audit import RetentionAudit
from tikrec.retention_execute import execute_retention


pytestmark = pytest.mark.skipif(os.name != "nt", reason="native Windows handle crash")

_CHILD = """
import os, sys
from pathlib import Path
from tests.test_retention_execute import fixture
from tikrec.retention_windows import HeldArtifact
from tikrec.retention_audit import RetentionAudit
root, parts, sid, config, jobs, audit, run = fixture(Path(sys.argv[1]))
phase = sys.argv[2]
set_info, prove, delete, append = (HeldArtifact._set, HeldArtifact.prove,
                                  HeldArtifact.delete, RetentionAudit.append)
def stop():
    os._exit(91)
def at_set(self, kind, buffer, size):
    set_info(self, kind, buffer, size)
    if (phase == 'renamed' and kind == 3 or phase == 'disposition' and kind == 4):
        stop()
def at_proof(self, digest):
    prove(self, digest)
    if phase == 'proved': stop()
def at_delete(self):
    delete(self)
    if phase == 'closed': stop()
def at_append(self, event, operation, **fields):
    if phase == 'all_deleted' and event == 'completed': stop()
    append(self, event, operation, **fields)
    if phase == 'deleted_record' and event == 'deleted': stop()
HeldArtifact._set, HeldArtifact.prove = at_set, at_proof
HeldArtifact.delete, RetentionAudit.append = at_delete, at_append
run()
"""


@pytest.mark.parametrize("phase", ["renamed", "proved", "disposition", "closed",
                                   "deleted_record", "all_deleted"])
def test_process_death_does_not_invent_completion_or_resume(tmp_path, phase):
    child = subprocess.run([sys.executable, "-c", _CHILD, str(tmp_path), phase],
                           capture_output=True, text=True, timeout=20)
    assert child.returncode == 91, child.stderr
    root, audit = tmp_path / "recordings", tmp_path / "audit" / "root.jsonl"
    records = events(audit)
    intent = records[0]
    assert not any(record["event"] in {"failed", "completed"} for record in records)
    original, private = root / intent["order"][0], root / intent["quarantine_order"][0]
    assert not original.exists()
    assert private.exists() == (phase in {"renamed", "proved"})
    count = sum(record["event"] == "deleted" for record in records)
    assert count == (len(intent["order"]) if phase == "all_deleted"
                     else 1 if phase == "deleted_record" else 0)
    assert (root / "alpha.mp4").exists() == (phase != "all_deleted")
    with RetentionAudit(root, audit):
        pass
    before = audit.read_bytes()
    with pytest.raises(ValueError, match="eligible"):
        execute_retention(root, intent["session_id"],
                          ConfigurationStore(tmp_path / "configuration.json"),
                          audit_path=audit,
                          job_paths=(tmp_path / "job.json", tmp_path / "job-2.json"),
                          clock=lambda: NOW, media_inspector=inspect)
    assert audit.read_bytes() == before
