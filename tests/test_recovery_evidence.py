"""Recovery evidence is append-only, fixed-schema, and resume-preflight compatible."""

import json

import pytest

from tests.test_reconciliation import saved_session
from tikrec.recovery_evidence import append_recovery_record, validate_recovery_record
from tikrec.session_resume import prepare_resume


def test_boundary_appends_without_allocating_or_replacing_connection(tmp_path):
    _, job, _ = saved_session(tmp_path)
    path = tmp_path / "out.parts/connections.jsonl"
    append_recovery_record(path, timestamp=2000, session_id=job.session_id,
                           reason="process_restart", resume_count=0)
    old = path.read_bytes()
    append_recovery_record(path, timestamp=2001, session_id=job.session_id,
                           reason="identity_unavailable", resume_count=0)
    assert path.read_bytes().startswith(old)
    session = prepare_resume(tmp_path / "out.parts", session_id=job.session_id)
    assert session.next_connection == 3


@pytest.mark.parametrize("changes", [
    {"reason": "https://cdn.test/live.flv?secret"}, {"resume_count": True},
    {"resume_count": -1}, {"timestamp": float("nan")}, {"session_id": "other"},
    {"url": "secret"}, {"event": "other"},
])
def test_malformed_recovery_boundary_is_refused(tmp_path, changes):
    _, job, _ = saved_session(tmp_path)
    record = {"event": "service_recovery", "timestamp": 2000, "session_id": job.session_id,
              "reason": "process_restart", "resume_count": 0, **changes}
    with pytest.raises(ValueError):
        validate_recovery_record(record, job.session_id)
    path = tmp_path / "out.parts/connections.jsonl"
    path.write_text(json.dumps(record) + "\n")
    with pytest.raises(ValueError):
        prepare_resume(tmp_path / "out.parts", session_id=job.session_id)
