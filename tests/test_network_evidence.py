"""Strict append-only outage summaries remain compatible with explicit session resume."""

import json
import socket

import pytest

from tests.test_live_recovery import FakeClock
from tests.test_reconciliation import saved_session
from tikrec.network_evidence import append_network_record, validate_network_record
from tikrec.retry_policy import OutageRecovery, RetryPolicy
from tikrec.session_resume import prepare_resume


def test_episode_boundaries_preserve_prior_bytes_and_reserve_no_media_connection(tmp_path):
    _, job, _ = saved_session(tmp_path)
    clock = FakeClock()
    recovery = OutageRecovery(RetryPolicy(), clock=clock)
    recovery.failure(socket.gaierror("DNS"))
    path = tmp_path / "out.parts/connections.jsonl"
    append_network_record(path, timestamp=clock(), session_id=job.session_id, phase="entered", recovery=recovery)
    before = path.read_bytes()
    clock.now += 5
    append_network_record(path, timestamp=clock(), session_id=job.session_id, phase="recovered", recovery=recovery)
    assert path.read_bytes().startswith(before)
    session = prepare_resume(tmp_path / "out.parts", session_id=job.session_id)
    assert session.next_connection == 3 and session.retained.next_index == 3


@pytest.mark.parametrize("changes", [
    {"phase": "unknown"}, {"failure_kind": "secret"}, {"retry_attempt": True},
    {"retry_attempt": 0}, {"timestamp": float("inf")}, {"outage_elapsed_seconds": -1},
    {"session_id": "other"}, {"url": "https://cdn.test/live.flv?secret"},
])
def test_malformed_network_summary_blocks_future_resume_without_repair(tmp_path, changes):
    _, job, _ = saved_session(tmp_path)
    record = {"event": "network_recovery", "timestamp": 1001, "session_id": job.session_id,
              "phase": "entered", "retry_attempt": 1, "outage_elapsed_seconds": 0,
              "failure_kind": "dns", **changes}
    with pytest.raises(ValueError):
        validate_network_record(record, job.session_id)
    path = tmp_path / "out.parts/connections.jsonl"
    path.write_text(json.dumps(record) + "\n")
    before = path.read_bytes()
    with pytest.raises(ValueError):
        prepare_resume(tmp_path / "out.parts", session_id=job.session_id)
    assert path.read_bytes() == before
