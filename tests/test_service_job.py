"""Non-secret service job mapping and stable per-user state paths."""

import json

from tests.test_reconciliation import saved_session
from tikrec.service_job import default_job_state_path, job_snapshot, persist_snapshot


def test_snapshot_roundtrip_keeps_resume_stop_and_completed_output(tmp_path):
    store, job, _ = saved_session(tmp_path, resume_count=2, stop_requested=True,
                                  state="completed", ended_at=1100, finalization_completed=True)
    snapshot = job_snapshot(job)
    snapshot["untrusted_url"] = "https://cdn.test/live.flv?secret"
    persist_snapshot(store, snapshot)
    assert store.load() == job
    assert snapshot["resumed"] and snapshot["resume_count"] == 2
    assert "secret" not in json.dumps(json.loads(store.path.read_text()))


def test_default_state_path_does_not_depend_on_working_directory(tmp_path, monkeypatch):
    original = default_job_state_path()
    monkeypatch.chdir(tmp_path)
    assert default_job_state_path() == original and original.is_absolute()
