"""Non-secret service job mapping and stable per-user state paths."""

import json
from unittest.mock import patch

from tests.test_reconciliation import saved_session
from tikrec.service_job import (default_job_state_path, job_snapshot,
                                persist_snapshot, progress_snapshot)
from tikrec.decode_diagnostics import input_decode_health


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


def test_progress_restores_manifest_reconnects_after_service_restart(tmp_path):
    parts = tmp_path / "out.parts"
    parts.mkdir()
    (parts / "part-0001.flv").write_bytes(b"media")
    (parts / "session.json").write_text(json.dumps({"reconnect_count": 7}))
    job = {"state": "completed", "started_at": 1000, "ended_at": 1100}

    restarted = progress_snapshot(job, parts=parts, active=False, current_part=None,
                                  current_bytes=0, resolutions=0, clock=lambda: 1200)
    with patch("pathlib.Path.read_text", side_effect=PermissionError("busy")):
        active = progress_snapshot(job, parts=parts, active=True, current_part=None,
                                   current_bytes=0, resolutions=10, clock=lambda: 1200)

    assert restarted["reconnect_count"] == 7
    assert active["reconnect_count"] == 9


def test_status_exposes_only_bounded_finalization_decode_health(tmp_path):
    parts = tmp_path / "out.parts"
    parts.mkdir()
    (parts / "part-0001.flv").write_bytes(b"media")
    health = input_decode_health("degraded", 2, ("h264_macroblock",))
    (parts / "session.json").write_text(json.dumps({
        "finalization": {"status": "completed", "input_decode": health},
    }))
    job = {"state": "completed", "started_at": 1000, "ended_at": 1100}
    snapshot = progress_snapshot(job, parts=parts, active=False, current_part=None,
                                 current_bytes=0, resolutions=0, clock=lambda: 1200)
    assert snapshot["input_decode_health"] == health

    health["diagnostic_codes"] = ["https://example.test/?token=secret"]
    (parts / "session.json").write_text(json.dumps({
        "finalization": {"status": "completed", "input_decode": health},
    }))
    snapshot = progress_snapshot(job, parts=parts, active=False, current_part=None,
                                 current_bytes=0, resolutions=0, clock=lambda: 1200)
    assert snapshot["input_decode_health"] == input_decode_health("unknown")
    assert "secret" not in json.dumps(snapshot)
