"""Offline read-only retention planning over actual session evidence."""

import hashlib
import json
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

from tests.test_session_parts import populate
from tikrec.configuration import Configuration
from tikrec.manifest import SessionManifest
from tikrec.media import MediaInfo
from tikrec.recovery_discovery import discover_recovery_candidates
from tikrec.retention_plan import plan_retention


MEDIA = MediaInfo("h264", "aac", 720, 1280, "mov,mp4", 12.5)
NOW = 2_000_000.0


def session(root: Path, name: str, *, creator="alpha", status="completed",
            finalization="completed", output=True, source="tiktok_live") -> Path:
    """Make a genuine schema-1 session and retained FLV part offline."""
    directory = root / f"{name}.parts"
    directory.mkdir()
    populate(directory, 1)
    target = root / f"{name}.mp4"
    if output:
        target.write_bytes(b"completed output")
    manifest = SessionManifest(directory, target, source, creator=creator if source == "tiktok_live" else None,
                               session_id=str(uuid.uuid4()), clock=iter((1000.0, 1010.0)).__next__,
                               media_inspector=lambda _: MEDIA)
    manifest.start(connection_count=1)
    parts = tuple(directory.glob("part-*.flv"))
    if status == "recording":
        manifest.update_capture(parts)
    else:
        manifest.finish(status, parts, output_path=target if output else None,
                        interrupted=status == "interrupted", finalization_status=finalization)
    return directory


def inspect(_: Path) -> MediaInfo:
    """Provide deterministic media proof without ffprobe or media decoding."""
    return MEDIA


def plan(root: Path, *, protected=(), days=1, now=NOW) -> list[dict]:
    """Return session decisions using an injected clock and media inspector."""
    config = Configuration(retention_protected_creators=protected, retention_max_age_days=days)
    return plan_retention(root, config, clock=lambda: now, media_inspector=inspect)["sessions"]


def test_age_boundary_protection_and_deterministic_order(tmp_path: Path) -> None:
    session(tmp_path, "zeta", creator="zeta")
    session(tmp_path, "alpha", creator="alpha")
    ended = 1010.0
    records = plan(tmp_path, protected=("zeta",), now=ended + 86400)
    assert [Path(item["parts_directory"]).name for item in records] == ["alpha.parts", "zeta.parts"]
    assert [(item["classification"], item["reason"]) for item in records] == [
        ("eligible", "age_threshold_reached"), ("protected", "protected_creator")]
    newer = plan(tmp_path, now=ended + 86400 - 1)
    assert all(item["reason"] == "not_old_enough" for item in newer)


def test_disabled_and_unknown_creator_never_eligible(tmp_path: Path) -> None:
    directory = session(tmp_path, "alpha", creator="alpha")
    assert plan(tmp_path, days=None)[0]["reason"] == "retention_disabled"
    path = directory / "session.json"
    values = json.loads(path.read_text())
    values.pop("creator")
    path.write_text(json.dumps(values))
    assert plan(tmp_path)[0]["reason"] == "creator_unknown"


@pytest.mark.parametrize("status,finalization,output", [
    ("recording", "pending", False),
    ("interrupted", "interrupted", False),
    ("failed", "failed", False),
    ("completed", "completed", False),
])
def test_incomplete_and_conflicting_sessions_are_not_eligible(
    tmp_path: Path, status: str, finalization: str, output: bool,
) -> None:
    session(tmp_path, "alpha", status=status, finalization=finalization, output=output)
    assert plan(tmp_path)[0]["classification"] != "eligible"


def test_malformed_symlink_and_direct_sources_are_not_eligible(tmp_path: Path,
                                                               monkeypatch) -> None:
    session(tmp_path, "direct", source="direct_flv")
    bad = session(tmp_path, "bad")
    manifest_path = bad / "session.json"
    original_bytes = manifest_path.read_bytes()
    manifest_path.write_text("{", encoding="utf-8")
    # An unreadable immediate claimant cannot prove its UUID or output unique.
    assert {item["reason"] for item in plan(tmp_path)} == {"evidence_conflict"}
    manifest_path.write_bytes(original_bytes)
    real_is_symlink = Path.is_symlink
    monkeypatch.setattr(Path, "is_symlink", lambda path:
                        path == manifest_path or real_is_symlink(path))
    assert next(item for item in plan(tmp_path) if item["parts_directory"] == str(bad))["reason"] == "evidence_conflict"


def test_plan_changes_zero_artifact_bytes_or_mtimes(tmp_path: Path) -> None:
    session(tmp_path, "alpha")
    (tmp_path / "job-state.json").write_text('{"state":"completed"}')
    config = Configuration(retention_max_age_days=1)
    def snapshot():
        return {str(path): (path.lstat().st_mode, path.lstat().st_size,
                            path.lstat().st_mtime_ns,
                            hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None)
                for path in (tmp_path, *tmp_path.rglob("*"))}
    before, settings = snapshot(), repr(config)
    assert plan_retention(tmp_path, config, clock=lambda: NOW,
                          media_inspector=inspect)["sessions"][0]["classification"] == "eligible"
    after = snapshot()
    assert after == before
    assert repr(config) == settings


def test_unrecognized_and_changing_evidence_fail_closed(tmp_path: Path) -> None:
    directory = session(tmp_path, "alpha")
    unknown = directory / "untracked.bin"
    unknown.write_bytes(b"preserve")
    assert plan(tmp_path)[0]["reason"] == "evidence_conflict"
    unknown.unlink()
    output = tmp_path / "alpha.mp4"
    def changing(_):
        output.write_bytes(output.read_bytes() + b"changed")
        return MEDIA
    result = plan_retention(tmp_path, Configuration(retention_max_age_days=1),
                            clock=lambda: NOW, media_inspector=changing)
    assert result["sessions"][0]["classification"] == "needs_attention"


def test_external_declared_output_is_not_inspected(tmp_path: Path) -> None:
    directory = session(tmp_path, "alpha")
    manifest_path = directory / "session.json"
    values = json.loads(manifest_path.read_text())
    values["output_path"] = str(tmp_path.parent / "outside.mp4")
    manifest_path.write_text(json.dumps(values), encoding="utf-8")
    observed = []
    result = plan_retention(tmp_path, Configuration(retention_max_age_days=1),
                            clock=lambda: NOW,
                            media_inspector=lambda path: observed.append(path) or MEDIA)
    assert result["sessions"][0]["classification"] == "needs_attention"
    assert observed == []


def test_plan_only_inspects_immediate_children_and_conflicting_ids(tmp_path: Path) -> None:
    first = session(tmp_path, "alpha")
    second = session(tmp_path, "beta", creator="beta")
    nested = tmp_path / "nested"
    nested.mkdir()
    session(nested, "hidden")
    second_manifest = second / "session.json"
    values = json.loads(second_manifest.read_text())
    values["session_id"] = json.loads((first / "session.json").read_text())["session_id"]
    second_manifest.write_text(json.dumps(values), encoding="utf-8")
    records = plan(tmp_path)
    assert len(records) == 2
    assert all(item["reason"] == "evidence_conflict" for item in records)


def change(directory: Path, **updates) -> dict:
    """Change one offline fixture manifest without touching its media."""
    path = directory / "session.json"
    values = json.loads(path.read_text())
    values.update(updates)
    path.write_text(json.dumps(values), encoding="utf-8")
    return values


@pytest.mark.parametrize("protected", [(), ("beta",)])
def test_rejected_competing_output_claim_blocks_eligible_owner(tmp_path, protected):
    session(tmp_path, "alpha")
    beta = session(tmp_path, "beta", creator="beta")
    change(beta, output_path=str(tmp_path / "alpha.mp4"))
    records = plan(tmp_path, protected=protected)
    assert all(item["reason"] == "evidence_conflict" for item in records)


def test_duplicate_uuid_survives_unrecognized_evidence(tmp_path):
    alpha = session(tmp_path, "alpha")
    beta = session(tmp_path, "beta", creator="beta")
    change(beta, session_id=json.loads((alpha / "session.json").read_text())["session_id"])
    (beta / "unrecognized.txt").write_text("preserve")
    assert all(item["reason"] == "evidence_conflict" for item in plan(tmp_path))


def test_unrecognized_competing_output_claim_blocks_owner(tmp_path):
    session(tmp_path, "alpha")
    beta = session(tmp_path, "beta", creator="beta")
    change(beta, output_path=str(tmp_path / "alpha.mp4"))
    (beta / "unrecognized.txt").write_text("preserve")
    assert all(item["reason"] == "evidence_conflict" for item in plan(tmp_path))


def test_unreadable_immediate_claim_cannot_prove_other_owner_unique(tmp_path):
    session(tmp_path, "alpha")
    beta = session(tmp_path, "beta", creator="beta")
    (beta / "session.json").write_text("{")
    assert all(item["reason"] == "evidence_conflict" for item in plan(tmp_path))


def test_claim_change_between_discovery_and_inspection_fails_closed(tmp_path, monkeypatch):
    import tikrec.retention_plan as module
    session(tmp_path, "alpha")
    original = module._claims
    def changing(directory, root):
        claims = original(directory, root)
        change(directory, session_id=str(uuid.uuid4()))
        return claims
    monkeypatch.setattr(module, "_claims", changing)
    assert plan(tmp_path)[0]["reason"] == "evidence_conflict"


@pytest.mark.parametrize("evidence", [
    {"event": "room_status", "timestamp": 100000.0, "status": 2,
     "confirmation_reached": True},
    {"event": "capture_resume", "timestamp": 100000.0, "reason": "explicit_resume",
     "previous_status": "interrupted", "connection": 2, "next_part_index": 2},
    {"event": "service_recovery", "timestamp": 100000.0,
     "reason": "process_restart", "resume_count": 1},
    {"event": "network_recovery", "timestamp": 100000.0, "phase": "entered",
     "retry_attempt": 1, "outage_elapsed_seconds": 0, "failure_kind": "timeout"},
    {"connection": 1, "ended_at": 100000.0},
])
def test_newer_connection_evidence_blocks_old_terminal_time(tmp_path, evidence):
    directory = session(tmp_path, "alpha")
    if evidence.get("event") == "capture_resume":
        change(directory, connection_count=2, reconnect_count=1)
    if evidence.get("event") in {"capture_resume", "service_recovery", "network_recovery"}:
        evidence["session_id"] = json.loads((directory / "session.json").read_text())["session_id"]
    (directory / "connections.jsonl").write_text(json.dumps(evidence) + "\n")
    assert discover_recovery_candidates(directory, media_inspector=inspect)[0].classification == "complete"
    assert plan(tmp_path)[0]["classification"] != "eligible"


def test_newer_valid_writer_recovery_blocks_old_terminal_time(tmp_path):
    from tikrec.writer_recovery_evidence import evidence_name
    directory = session(tmp_path, "alpha")
    values = json.loads((directory / "session.json").read_text())
    source = (directory / "part-0001.flv").read_bytes()
    name = evidence_name(values["session_id"], 1)
    (directory / name).write_bytes(source)
    change(directory, writer_recoveries=[{
        "timestamp": 100000.0, "part": "part-0001.flv", "evidence": name,
        "source_sha256": hashlib.sha256(source).hexdigest(), "source_bytes": len(source),
        "recovered_bytes": len(source), "discarded_trailing_bytes": 0,
    }], recovery_performed=True)
    assert discover_recovery_candidates(directory, media_inspector=inspect)[0].classification == "complete"
    assert plan(tmp_path)[0]["classification"] != "eligible"


@pytest.mark.parametrize("elapsed", [float("nan"), float("inf"), 1.0])
def test_invalid_elapsed_time_blocks_retention(tmp_path, elapsed):
    directory = session(tmp_path, "alpha")
    change(directory, elapsed_seconds=elapsed)
    assert plan(tmp_path)[0]["classification"] != "eligible"


@pytest.mark.parametrize("updates", [
    {"interrupted": True},
    {"error": "capture failed"},
    {"finalization": {"status": "completed", "error": "encoder failed"}},
])
def test_contradictory_success_blocks_retention(tmp_path, updates):
    directory = session(tmp_path, "alpha")
    change(directory, **updates)
    assert plan(tmp_path)[0]["classification"] != "eligible"


def test_recovery_history_alone_does_not_block_retention(tmp_path):
    directory = session(tmp_path, "alpha")
    change(directory, recovery_performed=True)
    assert plan(tmp_path)[0]["classification"] == "eligible"


@pytest.mark.skipif(sys.platform != "win32", reason="native junction requires Windows")
def test_native_junction_child_cannot_escape_root(tmp_path):
    outside = tmp_path.parent / f"outside-{uuid.uuid4()}"
    outside.mkdir()
    try:
        stored = session(outside, "alpha")
        change(stored, output_path=str(tmp_path / "alpha.mp4"))
        (tmp_path / "alpha.mp4").write_bytes(b"completed output")
        junction = tmp_path / "alpha.parts"
        result = subprocess.run(["cmd", "/c", "mklink", "/J", str(junction),
                                 str(outside / "alpha.parts")], capture_output=True)
        if result.returncode:
            pytest.skip("native junction creation unavailable")
        assert plan(tmp_path)[0]["classification"] != "eligible"
    finally:
        if (tmp_path / "alpha.parts").exists():
            (tmp_path / "alpha.parts").rmdir()
        for path in (outside / "alpha.parts").iterdir():
            path.unlink()
        (outside / "alpha.parts").rmdir()
        (outside / "alpha.mp4").unlink()
        outside.rmdir()


@pytest.mark.skipif(sys.platform != "win32", reason="native junction requires Windows")
def test_native_junction_root_is_rejected(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    session(real, "alpha")
    junction = tmp_path / "redirected"
    result = subprocess.run(["cmd", "/c", "mklink", "/J", str(junction), str(real)],
                            capture_output=True)
    if result.returncode:
        pytest.skip("native junction creation unavailable")
    try:
        with pytest.raises(ValueError, match="redirect"):
            plan(junction)
    finally:
        junction.rmdir()
