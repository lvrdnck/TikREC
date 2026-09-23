"""Offline read-only retention planning over actual session evidence."""

import hashlib
import json
import uuid
from pathlib import Path

import pytest

from tests.test_session_parts import populate
from tikrec.configuration import Configuration
from tikrec.manifest import SessionManifest
from tikrec.media import MediaInfo
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
    assert {item["reason"] for item in plan(tmp_path)} == {
        "source_not_tiktok_live", "evidence_conflict"}
    manifest_path.write_bytes(original_bytes)
    real_is_symlink = Path.is_symlink
    monkeypatch.setattr(Path, "is_symlink", lambda path:
                        path == manifest_path or real_is_symlink(path))
    assert next(item for item in plan(tmp_path) if item["parts_directory"] == str(bad))["reason"] == "evidence_conflict"


def test_plan_changes_zero_artifact_bytes_or_mtimes(tmp_path: Path) -> None:
    session(tmp_path, "alpha")
    before = {str(path): (hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_mtime_ns)
              for path in tmp_path.rglob("*") if path.is_file()}
    assert plan(tmp_path)[0]["classification"] == "eligible"
    after = {str(path): (hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_mtime_ns)
             for path in tmp_path.rglob("*") if path.is_file()}
    assert after == before


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
