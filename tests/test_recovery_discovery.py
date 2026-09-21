"""Offline checks for conservative, read-only recovery discovery."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.test_session_parts import populate
from tikrec.manifest import SessionManifest
from tikrec.media import MediaInfo
from tikrec.recovery_discovery import discover_recovery_candidates


ID = "a738109c-a387-423f-a20b-969ecf656c4b"
MEDIA = MediaInfo("h264", "aac", 720, 1280, "mov,mp4", 12.5)


def make_session(
    root: Path,
    *,
    name: str = "creator.parts",
    status: str = "interrupted",
    finalization: str = "interrupted",
    output_declared: bool = True,
    output_exists: bool = False,
) -> tuple[Path, Path | None]:
    directory = root / name
    directory.mkdir()
    populate(directory, 1)
    output = root / f"{Path(name).stem}.mp4" if output_declared else None
    manifest = SessionManifest(
        directory, output, "tiktok_live", clock=iter((1000.0, 1010.0)).__next__,
        session_id=ID, media_inspector=lambda _: MEDIA,
    )
    manifest.start(connection_count=1)
    manifest.record_room_identity("7687950152400816913")
    parts = tuple(directory.glob("part-*.flv"))
    if output_exists:
        assert output is not None
        output.write_bytes(b"completed output")
    if status == "recording":
        manifest.update_capture(parts)
    else:
        manifest.finish(
            status, parts, output_path=output if output_exists else None,
            interrupted=status == "interrupted", finalization_status=finalization,
            error="capture or finalization failed" if status == "failed" else None,
        )
    return directory, output


def inspect(_: Path) -> MediaInfo:
    return MEDIA


def snapshot(directory: Path) -> dict[str, tuple[bytes, int]]:
    return {
        path.name: (path.read_bytes(), path.stat().st_mtime_ns)
        for path in directory.iterdir() if path.is_file()
    }


def test_completed_session_reports_nothing_to_recover(tmp_path: Path) -> None:
    directory, output = make_session(
        tmp_path, status="completed", finalization="completed", output_exists=True
    )

    candidate, = discover_recovery_candidates(directory, media_inspector=inspect)

    assert candidate.session_id == ID
    assert candidate.source_type == "tiktok_live"
    assert candidate.room_id == "7687950152400816913"
    assert candidate.output_path == str(output)
    assert candidate.retained_parts == 1
    assert candidate.final_output == "present"
    assert candidate.finalization_state == "complete"
    assert candidate.classification == "complete"
    assert candidate.safe_next_action
    assert candidate.summary == "Final output already exists — nothing to recover."


def test_interrupted_session_with_valid_parts_is_recoverable(tmp_path: Path) -> None:
    directory, output = make_session(tmp_path)

    candidate, = discover_recovery_candidates(directory, media_inspector=inspect)

    assert candidate.lifecycle_state == "interrupted"
    assert candidate.final_output == "missing"
    assert candidate.finalization_state == "incomplete"
    assert candidate.evidence_consistent
    assert candidate.classification == "recoverable"
    assert candidate.safe_next_action
    assert str(output) in candidate.output_path
    assert "parts appear available" in candidate.summary


def test_failed_finalization_can_be_safely_retried(tmp_path: Path) -> None:
    directory, _ = make_session(
        tmp_path, status="failed", finalization="failed"
    )

    candidate, = discover_recovery_candidates(directory, media_inspector=inspect)

    assert candidate.finalization_state == "failed"
    assert candidate.classification == "recoverable"
    assert "safe repeat attempt" in candidate.summary


def test_running_finalization_is_left_untouched(tmp_path: Path) -> None:
    directory, _ = make_session(
        tmp_path, status="interrupted", finalization="running"
    )

    candidate, = discover_recovery_candidates(directory, media_inspector=inspect)

    assert candidate.classification == "active_or_uncertain"
    assert not candidate.safe_next_action
    assert "cannot be ruled out" in candidate.untouched_reason


@pytest.mark.parametrize("manifest", ["missing", "malformed"])
def test_missing_or_malformed_manifest_is_ambiguous(tmp_path: Path, manifest: str) -> None:
    directory, _ = make_session(tmp_path)
    path = directory / "session.json"
    if manifest == "missing":
        path.unlink()
    else:
        path.write_text("{not-json", encoding="utf-8")

    candidate, = discover_recovery_candidates(directory, media_inspector=inspect)

    assert candidate.retained_parts == 1
    assert candidate.session_id is None
    assert candidate.classification == "needs_attention"
    assert not candidate.evidence_consistent
    assert not candidate.safe_next_action
    assert "will not modify" in candidate.summary


def test_existing_output_conflicting_with_failed_state_is_untouched(tmp_path: Path) -> None:
    directory, output = make_session(
        tmp_path, status="failed", finalization="failed"
    )
    assert output is not None
    output.write_bytes(b"ambiguous output")

    candidate, = discover_recovery_candidates(directory, media_inspector=inspect)

    assert candidate.final_output == "present"
    assert candidate.classification == "needs_attention"
    assert "without matching" in candidate.untouched_reason


def test_writer_partial_blocks_guidance_and_is_preserved(tmp_path: Path) -> None:
    directory, _ = make_session(tmp_path, status="recording", finalization="pending")
    partial = directory / ".part-0002.flv.partial"
    partial.write_bytes(b"keep this evidence")

    candidate, = discover_recovery_candidates(directory, media_inspector=inspect)

    assert candidate.classification == "needs_attention"
    assert "partial" in candidate.untouched_reason
    assert partial.read_bytes() == b"keep this evidence"


@pytest.mark.parametrize("name", [
    f".tikrec-writer-crash-{ID}-part-0002.evidence",
    f".tikrec-writer-recovery-{ID}-part-0002.tmp",
])
def test_uncommitted_writer_recovery_artifact_blocks_guidance(
    tmp_path: Path, name: str
) -> None:
    directory, _ = make_session(tmp_path)
    artifact = directory / name
    artifact.write_bytes(b"preserve")

    candidate, = discover_recovery_candidates(directory, media_inspector=inspect)

    assert candidate.classification == "needs_attention"
    assert "service evidence" in candidate.untouched_reason
    assert artifact.read_bytes() == b"preserve"


def test_encoder_partial_blocks_manual_finalization_guidance(tmp_path: Path) -> None:
    directory, output = make_session(tmp_path)
    assert output is not None
    partial = output.with_name(f".{output.stem}.partial{output.suffix}")
    partial.write_bytes(b"preserve")

    candidate, = discover_recovery_candidates(directory, media_inspector=inspect)

    assert candidate.classification == "needs_attention"
    assert "ownership-aware" in candidate.untouched_reason
    assert partial.read_bytes() == b"preserve"


def test_empty_root_has_no_candidates_and_scan_is_not_recursive(tmp_path: Path) -> None:
    assert discover_recovery_candidates(tmp_path, media_inspector=inspect) == ()
    nested = tmp_path / "nested"
    nested.mkdir()
    make_session(nested)
    assert discover_recovery_candidates(tmp_path, media_inspector=inspect) == ()


def test_root_discovers_only_immediate_parts_directories_in_stable_order(tmp_path: Path) -> None:
    second, _ = make_session(tmp_path, name="B.parts")
    first, _ = make_session(tmp_path, name="a.parts")

    candidates = discover_recovery_candidates(tmp_path, media_inspector=inspect)

    assert [Path(item.parts_directory) for item in candidates] == [first, second]


def test_discovery_does_not_mutate_any_session_artifact(tmp_path: Path) -> None:
    directory, _ = make_session(tmp_path)
    before = snapshot(directory)

    discover_recovery_candidates(directory, media_inspector=inspect)

    assert snapshot(directory) == before


def test_duplicate_manifest_fields_fail_closed(tmp_path: Path) -> None:
    directory, _ = make_session(tmp_path)
    path = directory / "session.json"
    values = json.loads(path.read_text(encoding="utf-8"))
    text = json.dumps(values)
    path.write_text(text[:-1] + ', "status": "completed"}', encoding="utf-8")

    candidate, = discover_recovery_candidates(directory, media_inspector=inspect)

    assert candidate.classification == "needs_attention"
    assert "duplicate" in candidate.untouched_reason
