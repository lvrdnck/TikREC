"""Offline durability and conservative eligibility checks for service intent."""

import json
from dataclasses import asdict, replace
from unittest.mock import patch

import pytest

from tikrec.job_state import JobState, JobStateError, JobStateStore


PAGE = "https://www.tiktok.com/@creator/live"


def intent(tmp_path):
    return JobState(
        session_id="a738109c-a387-423f-a20b-969ecf656c4b",
        source_url=PAGE, output_path=str(tmp_path / "out.mp4"),
        parts_directory=str(tmp_path / "out.parts"), started_at=123.0,
    )


def test_missing_state_is_idle_without_creating_storage(tmp_path):
    store = JobStateStore(tmp_path / "service" / "job.json")
    assert store.load() is None
    assert not store.path.parent.exists()


def test_round_trip_and_single_latest_job(tmp_path):
    store = JobStateStore(tmp_path / "service" / "job.json")
    job = intent(tmp_path)
    store.save(job)
    assert JobStateStore(store.path).load() == job
    updated = replace(job, state="recording", room_id="12345", resume_count=2)
    store.save(updated)
    assert store.load() == updated
    assert list(store.path.parent.iterdir()) == [store.path]


@pytest.mark.parametrize("state", ["resolving", "recovering", "reconciling",
                                  "resuming", "recording", "reconnecting"])
def test_active_intent_requires_proven_identity_to_resume(tmp_path, state):
    job = replace(intent(tmp_path), state=state)
    assert job.needs_reconciliation
    assert not job.may_resume
    assert replace(job, room_id="12345").may_resume


@pytest.mark.parametrize("changes", [
    {"stop_requested": True}, {"state": "finalizing"},
    {"finalization_completed": True}, {"state": "completed", "ended_at": 124.0},
    {"state": "failed", "ended_at": 124.0},
])
def test_stop_and_finalization_never_allow_capture_resume(tmp_path, changes):
    job = replace(intent(tmp_path), room_id="12345", **changes)
    assert not job.may_resume


def test_nonterminal_stopped_job_still_needs_finalization_reconciliation(tmp_path):
    job = replace(intent(tmp_path), stop_requested=True)
    assert job.needs_reconciliation
    assert not job.may_resume


def test_completed_finalization_does_not_need_reconciliation(tmp_path):
    job = replace(intent(tmp_path), finalization_completed=True)
    assert not job.needs_reconciliation
    assert not job.may_resume


@pytest.mark.parametrize("changes", [
    {"schema_version": 2}, {"schema_version": True}, {"session_id": "unknown"},
    {"source_url": PAGE + "?token=secret"}, {"source_url": PAGE + "#secret"},
    {"source_url": "https://cdn.test/live.flv?signature=secret"},
    {"source_url": "https://secret@www.tiktok.com/@creator/live"},
    {"output_path": "relative.mp4"}, {"output_path": "\x00bad.mp4"},
    {"output_path": "https://cdn.test/out.mp4"},
    {"parts_directory": "relative.parts"}, {"started_at": float("inf")},
    {"started_at": True}, {"started_at": -1}, {"ended_at": 122.0},
    {"state": "unknown"}, {"stop_requested": "false"},
    {"finalization_completed": 1}, {"resume_count": -1}, {"resume_count": True},
    {"room_id": "https://cdn.test/secret"}, {"room_id": 123}, {"room_id": ""},
    {"room_id": "0"}, {"room_id": "00123"}, {"room_id": "１２３"},
    {"recovery_reason": "Bearer secret"},
    {"state": "completed"}, {"state": "failed"},
])
def test_invalid_state_is_rejected_without_modifying_durable_intent(tmp_path, changes):
    store = JobStateStore(tmp_path / "job.json")
    job = intent(tmp_path)
    store.save(job)
    original = store.path.read_bytes()
    with pytest.raises(JobStateError):
        store.save(replace(job, **changes))
    assert store.path.read_bytes() == original


@pytest.mark.parametrize("body", ["{", "[]", "null", '{"schema_version":1}',
                                  '{"schema_version":NaN}'])
def test_ambiguous_json_is_preserved_and_fails_safely(tmp_path, body):
    path = tmp_path / "job.json"
    path.write_text(body, encoding="utf-8")
    with pytest.raises(JobStateError, match="invalid durable job state"):
        JobStateStore(path).load()
    assert path.read_text(encoding="utf-8") == body


def test_unknown_secret_fields_fail_without_reflecting_values(tmp_path):
    path = tmp_path / "job.json"
    values = asdict(intent(tmp_path))
    values["bearer_token"] = "do-not-reflect-this-secret"
    path.write_text(json.dumps(values), encoding="utf-8")
    with pytest.raises(JobStateError) as failure:
        JobStateStore(path).load()
    assert "secret" not in str(failure.value)


def test_atomic_promotion_exposes_old_or_complete_new_json(tmp_path):
    store = JobStateStore(tmp_path / "job.json")
    job = intent(tmp_path)
    store.save(job)
    updated = replace(job, stop_requested=True)
    import os
    promote = os.replace

    def inspect_before_replace(source, target):
        assert store.load() == job
        assert json.loads(source.read_text(encoding="utf-8")) == asdict(updated)
        promote(source, target)

    with patch("tikrec.job_state.os.replace", side_effect=inspect_before_replace):
        store.save(updated)
    assert store.load() == updated


@pytest.mark.parametrize("operation", ["os.fsync", "os.replace"])
def test_failed_write_preserves_previous_state_and_unrelated_evidence(tmp_path, operation):
    store = JobStateStore(tmp_path / "job.json")
    job = intent(tmp_path)
    store.save(job)
    evidence = tmp_path / ".job.json.old.partial"
    evidence.write_bytes(b"crash evidence")
    with patch("tikrec.job_state." + operation, side_effect=OSError("disk failure")):
        with pytest.raises(OSError):
            store.save(replace(job, stop_requested=True))
    assert store.load() == job
    assert evidence.read_bytes() == b"crash evidence"
    assert set(tmp_path.iterdir()) == {store.path, evidence}


def test_stale_temporary_json_is_not_committed_intent(tmp_path):
    path = tmp_path / "job.json"
    partial = tmp_path / ".job.json.crashed.partial"
    partial.write_text(json.dumps(asdict(intent(tmp_path))), encoding="utf-8")
    assert JobStateStore(path).load() is None
    assert partial.exists()


def test_persisted_fields_contain_only_public_identity_and_fixed_reasons(tmp_path):
    store = JobStateStore(tmp_path / "job.json")
    job = replace(intent(tmp_path), room_id="12345", recovery_reason="process_restart")
    store.save(job)
    text = store.path.read_text(encoding="utf-8")
    assert "signature" not in text and "token" not in text and "cookie" not in text
    assert json.loads(text)["source_url"] == PAGE


def test_parts_path_must_belong_to_requested_output(tmp_path):
    store = JobStateStore(tmp_path / "job.json")
    with pytest.raises(JobStateError):
        store.save(replace(intent(tmp_path), parts_directory=str(tmp_path / "other.parts")))
    assert not store.path.exists()


def test_duplicate_stop_flag_is_ambiguous(tmp_path):
    path = tmp_path / "job.json"
    body = json.dumps(asdict(intent(tmp_path)))
    body = body[:-1] + ', "stop_requested": true}'
    path.write_text(body, encoding="utf-8")
    with pytest.raises(JobStateError):
        JobStateStore(path).load()
    assert path.read_text(encoding="utf-8") == body


@pytest.mark.parametrize("field", ["stop_requested", "room_id", "finalization_completed"])
def test_missing_safety_field_does_not_acquire_a_default(tmp_path, field):
    path = tmp_path / "job.json"
    values = asdict(intent(tmp_path))
    del values[field]
    path.write_text(json.dumps(values), encoding="utf-8")
    with pytest.raises(JobStateError):
        JobStateStore(path).load()


def test_invalid_utf8_state_is_preserved(tmp_path):
    path = tmp_path / "job.json"
    path.write_bytes(b"\xff")
    with pytest.raises(JobStateError):
        JobStateStore(path).load()
    assert path.read_bytes() == b"\xff"


def test_committed_file_is_synced_before_promotion(tmp_path):
    store = JobStateStore(tmp_path / "job.json")
    import os
    sync, promote = os.fsync, os.replace
    events = []

    def synced(descriptor):
        events.append("sync")
        sync(descriptor)

    def promoted(source, target):
        assert events == ["sync"]
        events.append("promote")
        promote(source, target)

    with patch("tikrec.job_state.os.fsync", side_effect=synced), \
            patch("tikrec.job_state.os.replace", side_effect=promoted):
        store.save(intent(tmp_path))
    assert events[:2] == ["sync", "promote"]


def test_resolved_room_identity_is_persisted_without_signed_transport(tmp_path):
    from tests.test_tiktok import _Opener, live_page, live_room
    from tikrec.tiktok import resolve_live

    signed = "https://cdn.test/live.flv?signature=do-not-persist"
    result = resolve_live(PAGE, opener=_Opener([live_page("00123"), live_room({"HD1": signed})]))
    store = JobStateStore(tmp_path / "job.json")
    store.save(replace(intent(tmp_path), room_id=result.room_id))
    assert store.load().room_id == "123"
    body = store.path.read_text(encoding="utf-8")
    assert signed not in body and "do-not-persist" not in body and "flv_url" not in body
    with pytest.raises(JobStateError):
        store.save(replace(intent(tmp_path), room_id=result))
    assert store.load().room_id == "123"
