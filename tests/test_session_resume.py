"""Offline preflight checks: ambiguous session state must remain unchanged."""

import json

import pytest

from tests.test_session_parts import populate
from tikrec.manifest import SessionManifest
from tikrec.session_resume import prepare_resume


ID = "a738109c-a387-423f-a20b-969ecf656c4b"


def session(tmp_path, *, output=None, status="interrupted", connection_count=1):
    directory = tmp_path / "session.parts"
    directory.mkdir()
    populate(directory)
    manifest = SessionManifest(directory, output, "direct_flv", clock=lambda: 1000,
                               session_id=ID, media_inspector=lambda _: None)
    manifest.start(connection_count=connection_count)
    if status == "recording":
        manifest.update_capture(tuple(directory.glob("*.flv")))
    else:
        manifest.finish(status, tuple(directory.glob("*.flv")),
                        interrupted=status == "interrupted",
                        finalization_status="not_started" if output else "not_requested")
    return directory


def update(directory, **values):
    path = directory / "session.json"
    document = json.loads(path.read_text())
    document.update(values)
    path.write_text(json.dumps(document))


def test_preflight_is_read_only_and_preserves_identity(tmp_path):
    directory = session(tmp_path)
    before = {p.name: p.read_bytes() for p in directory.iterdir()}
    result = prepare_resume(directory, clock=lambda: 2000, session_id=ID)
    assert result.session_id == ID and result.next_connection == 2
    assert result.retained.next_index == 3
    assert before == {p.name: p.read_bytes() for p in directory.iterdir()}


@pytest.mark.parametrize("changes", [
    {"session_id": "bad"}, {"schema_version": True}, {"schema_version": 2},
    {"source_type": "unknown"}, {"status": "completed"}, {"status": "unknown"},
    {"part_count": 3}, {"part_count": 1}, {"part_count": True},
    {"connection_count": -1}, {"connection_count": True}, {"reconnect_count": 3},
    {"started_at": None}, {"started_at": float("inf")}, {"ended_at": 999},
    {"interrupted": "false"}, {"room_id": "https://cdn.test/secret"},
    {"interrupted": False},
    {"parts_directory": "other.parts"},
    {"output_path": "https://cdn.test/live.flv?secret=x"}, {"output_path": "no_suffix"},
    {"finalization": {"status": "running"}},
    {"finalization": {"status": "completed"}},
    {"finalization": {"status": "failed"}},
])
def test_invalid_session_fails_without_writes(tmp_path, changes):
    directory = session(tmp_path)
    update(directory, **changes)
    before = {p.name: p.read_bytes() for p in directory.iterdir()}
    with pytest.raises(ValueError):
        prepare_resume(directory)
    assert before == {p.name: p.read_bytes() for p in directory.iterdir()}


def test_active_manifest_can_lag_promoted_parts(tmp_path):
    directory = session(tmp_path, status="recording")
    update(directory, part_count=0)
    assert len(prepare_resume(directory).retained.parts) == 2


def test_legacy_parts_without_manifest_are_not_resumable(tmp_path):
    populate(tmp_path)
    with pytest.raises(ValueError, match="manifest"):
        prepare_resume(tmp_path)


def test_expected_session_or_source_conflict_fails(tmp_path):
    directory = session(tmp_path)
    with pytest.raises(ValueError):
        prepare_resume(directory, session_id="different")
    with pytest.raises(ValueError):
        prepare_resume(directory, source_type="tiktok_live")


def test_existing_output_or_finalizer_partial_blocks_resume(tmp_path):
    output = tmp_path / "final.mp4"
    directory = session(tmp_path, output=output)
    partial = tmp_path / ".final.partial.mp4"
    partial.write_bytes(b"incomplete")
    with pytest.raises(ValueError):
        prepare_resume(directory, output_path=output)
    assert partial.read_bytes() == b"incomplete"
    partial.unlink()
    output.write_bytes(b"completed")
    with pytest.raises(ValueError):
        prepare_resume(directory)
    assert output.read_bytes() == b"completed"


def test_requested_output_must_match_prior_declaration(tmp_path):
    directory = session(tmp_path, output=tmp_path / "final.mp4")
    with pytest.raises(ValueError):
        prepare_resume(directory, output_path=tmp_path / "different.mp4")


def test_connection_evidence_advances_past_stale_manifest_count(tmp_path):
    directory = session(tmp_path, status="recording")
    log = directory / "connections.jsonl"
    log.write_text(json.dumps({"connection": 3, "ended_at": 1500,
                               "part_start": "part-0001.flv", "part_end": "part-0002.flv"}) + "\n")
    result = prepare_resume(directory)
    assert result.next_connection == 4 and result.previous_end == 1500


@pytest.mark.parametrize("body", ["{", "{}\n", "[]\n",
    '{"connection":true,"ended_at":1500}\n',
    '{"connection":1,"ended_at":1500}\n{"connection":1,"ended_at":1600}\n',
    '{"connection":1,"ended_at":1500,"part_start":"part-0003.flv","part_end":"part-0003.flv"}\n',
    '{"event":"capture_resume","session_id":"different","connection":2}\n',
    '{"connection":1,"ended_at":1500,"part_start":"../part-0001.flv","part_end":"part-0001.flv"}\n',
    '{"event":"room_status"}\n',
])
def test_ambiguous_connection_log_is_not_repaired(tmp_path, body):
    directory = session(tmp_path)
    log = directory / "connections.jsonl"
    log.write_text(body)
    with pytest.raises(ValueError):
        prepare_resume(directory)
    assert log.read_text() == body


def test_duplicate_manifest_fields_fail(tmp_path):
    directory = session(tmp_path)
    path = directory / "session.json"
    path.write_text(path.read_text().rstrip()[:-1] + ',"status":"recording"}')
    with pytest.raises(ValueError):
        prepare_resume(directory)


def test_existing_public_identity_and_unknown_manifest_facts_survive(tmp_path):
    directory = session(tmp_path)
    update(directory, room_id="12345", custom_fact={"value": "retain"})
    result = prepare_resume(directory)
    assert result.manifest.snapshot()["room_id"] == "12345"
    assert result.manifest.snapshot()["custom_fact"] == {"value": "retain"}


def test_manifest_snapshot_cannot_mutate_loaded_state(tmp_path):
    directory = session(tmp_path)
    loaded = prepare_resume(directory).manifest
    copy = loaded.snapshot()
    copy["finalization"]["status"] = "completed"
    assert loaded.snapshot()["finalization"]["status"] == "not_requested"


def test_recording_manifest_cannot_have_closed_capture_timestamp(tmp_path):
    directory = session(tmp_path, status="recording")
    update(directory, ended_at=1000)
    with pytest.raises(ValueError):
        prepare_resume(directory)


@pytest.mark.parametrize("name", ["connections.jsonl", ".final.partial.mp4"])
def test_dangling_link_artifacts_are_not_treated_as_absent(tmp_path, monkeypatch, name):
    from pathlib import Path

    output = tmp_path / "final.mp4"
    directory = session(tmp_path, output=output)
    target = (directory if name == "connections.jsonl" else tmp_path) / name
    is_symlink = Path.is_symlink
    # Model a dangling link without requiring Windows symlink privileges in offline tests.
    monkeypatch.setattr(Path, "is_symlink", lambda path: path == target or is_symlink(path))
    with pytest.raises(ValueError):
        prepare_resume(directory, output_path=output)


def test_closed_manifest_cannot_lag_a_newer_connection_record(tmp_path):
    directory = session(tmp_path)
    log = directory / "connections.jsonl"
    log.write_text('{"connection":3,"ended_at":1500}\n')
    with pytest.raises(ValueError):
        prepare_resume(directory)
