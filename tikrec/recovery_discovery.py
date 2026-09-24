"""Read-only discovery and classification of interrupted TikREC sessions."""

from __future__ import annotations

import json
import math
import re
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path

from .retention_snapshot import ObservedInstability

from .finalize import _temporary_output_path
from .media import MediaInfo, inspect_media
from .session_parts import discover_parts
from .session_resume import _read_connections, _unique_values, _validate_manifest
from .tiktok_identity import canonical_room_id
from .writer_recovery_evidence import recovery_records

_PART_NAME = re.compile(r"part-[0-9]+\.flv")

@dataclass(frozen=True)
class RecoveryCandidate:
    """Safe facts and guidance for one possible recovery session."""

    parts_directory: str
    session_id: str | None
    source_type: str | None
    room_id: str | None
    output_path: str | None
    lifecycle_state: str
    retained_parts: int
    final_output: str
    finalization_state: str
    evidence_consistent: bool
    classification: str
    safe_next_action: bool
    summary: str
    next_action: str
    untouched_reason: str | None

    def as_dict(self) -> dict[str, object]:
        """Return stable JSON-ready recovery facts."""
        return asdict(self)

def discover_recovery_candidates(
    scope: Path,
    *,
    media_inspector: Callable[[Path], MediaInfo | None] = inspect_media,
    control_reader: Callable[[Path], bytes | None] | None = None,
) -> tuple[RecoveryCandidate, ...]:
    """Inspect one parts directory or immediate ``*.parts`` children read-only."""
    root = Path(scope)
    if root.is_symlink() or not root.is_dir():
        raise ValueError(f"recovery scope must be a regular directory: {root}")
    directories = (root,) if _is_candidate(root) else _child_candidates(root)
    return tuple(_inspect_candidate(path, media_inspector, control_reader)
                 for path in directories)

def _is_candidate(path: Path) -> bool:
    return (
        path.name.lower().endswith(".parts")
        or (path / "session.json").exists()
        or (path / "session.json").is_symlink()
        or any(_PART_NAME.fullmatch(child.name) for child in path.iterdir())
    )

def _child_candidates(root: Path) -> tuple[Path, ...]:
    children = (path for path in root.iterdir() if path.name.lower().endswith(".parts"))
    return tuple(sorted(children, key=lambda path: (path.name.casefold(), path.name)))

def _inspect_candidate(
    directory: Path,
    media_inspector: Callable[[Path], MediaInfo | None],
    control_reader: Callable[[Path], bytes | None] | None = None,
) -> RecoveryCandidate:
    if directory.is_symlink() or not directory.is_dir():
        return _unsafe(directory, 0, "candidate is not a regular directory")
    apparent_parts = _apparent_part_count(directory)
    manifest_path = directory / "session.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        return _unsafe(directory, apparent_parts, "supported session.json is missing")

    try:
        read_manifest = (lambda: _read_manifest(manifest_path) if control_reader is None
                         else _read_manifest(manifest_path, content=control_reader(manifest_path)))
        values = read_manifest()
        retained = discover_parts(directory)
        _validate_manifest(values, directory, retained, None, None,
                           finalization_recovery=True)
        _check_recovery_artifacts(directory, values)
        log = ({} if control_reader is None else
               {"content": control_reader(directory / "connections.jsonl")})
        connection_count, _ = _read_connections(directory, retained, values["session_id"],
                                                **log)
        if values["status"] != "recording" and connection_count > values["connection_count"]:
            raise ValueError("closed manifest predates newer connection evidence")
        # Refuse guidance when an active process changed evidence during inspection.
        if read_manifest() != values:
            raise ValueError("session evidence changed during inspection")
        output = _declared_output(directory, values)
    except ObservedInstability:
        raise
    except (OSError, UnicodeError, ValueError, TypeError, KeyError, AttributeError,
            OverflowError, json.JSONDecodeError) as error:
        return _unsafe(directory, apparent_parts, str(error))

    return _classify(directory, values, retained.parts, output, media_inspector)

def _read_manifest(path: Path, *, content: bytes | None = None) -> dict:
    values = json.loads((path.read_text(encoding="utf-8") if content is None
                         else content.decode("utf-8")), object_pairs_hook=_unique_values)
    if not isinstance(values, dict):
        raise ValueError("session manifest must be an object")
    return values


def _declared_output(directory: Path, values: dict) -> Path | None:
    declared = values.get("output_path")
    if declared is None:
        return None
    if (not isinstance(declared, str) or not declared or "\x00" in declared
            or "://" in declared):
        raise ValueError("manifest output path is invalid")
    output = Path(declared)
    if not output.suffix:
        raise ValueError("manifest output path lacks a container suffix")
    if output.is_absolute() or output.exists() or output.is_symlink():
        return output
    stored_parts = Path(values["parts_directory"]).parts
    actual_parts = directory.parts
    if stored_parts and len(actual_parts) >= len(stored_parts):
        if actual_parts[-len(stored_parts):] == stored_parts:
            return Path(*actual_parts[:-len(stored_parts)]) / output
    return output


def _classify(directory, values, parts, output, media_inspector):
    finalization = values["finalization"]["status"]
    lifecycle = values["status"]
    finalization_state = _finalization_state(finalization)
    facts = _facts(directory, values, len(parts), output, finalization_state)
    output_present = output is not None and (output.exists() or output.is_symlink())
    partial = None if output is None else _temporary_output_path(output)
    partial_present = partial is not None and (partial.exists() or partial.is_symlink())

    if output_present:
        if partial_present:
            return _conflict(facts, "final output and encoder partial coexist", "present")
        if finalization == "completed" and _output_is_proven(output, values, media_inspector):
            return RecoveryCandidate(
                **facts, final_output="present", evidence_consistent=True,
                classification="complete", safe_next_action=True,
                summary="Final output already exists — nothing to recover.",
                next_action="Keep the completed output and retained parts.",
                untouched_reason=None,
            )
        return _conflict(
            facts, "output exists without matching completed finalization evidence", "present"
        )

    if finalization == "completed":
        return _conflict(facts, "manifest claims completion but the final output is missing",
                         _output_state(output))
    if partial_present:
        return _conflict(facts, "unfinished encoder output requires ownership-aware recovery",
                         _output_state(output))
    if lifecycle == "recording" or finalization == "running":
        return RecoveryCandidate(
            **facts, final_output=_output_state(output), evidence_consistent=True,
            classification="active_or_uncertain", safe_next_action=False,
            summary="Session may still be active — TikREC will not modify it.",
            next_action="Check the recording service before attempting recovery.",
            untouched_reason="active recording or finalization cannot be ruled out",
        )

    if output is None:
        action = "Choose an output path and use tikrec finalize after reviewing this session."
    else:
        action = "Use tikrec finalize with this parts directory and the declared output path."
    summary = (
        "Finalization failed — retained parts appear available for a safe repeat attempt."
        if finalization == "failed"
        else "Recording ended before finalization — parts appear available for recovery."
    )
    return RecoveryCandidate(
        **facts, final_output=_output_state(output), evidence_consistent=True,
        classification="recoverable", safe_next_action=True, summary=summary,
        next_action=action, untouched_reason=None,
    )


def _facts(directory, values, count, output, finalization_state):
    return {
        "parts_directory": str(directory),
        "session_id": values["session_id"],
        "source_type": values["source_type"],
        "room_id": values.get("room_id"),
        "output_path": None if output is None else str(output),
        "lifecycle_state": values["status"],
        "retained_parts": count,
        "finalization_state": finalization_state,
    }


def _unsafe(directory: Path, count: int, reason: str) -> RecoveryCandidate:
    return RecoveryCandidate(
        str(directory), None, None, None, None, "unknown", count, "unknown",
        "unknown", False, "needs_attention", False,
        "Session evidence is incomplete or conflicting — TikREC will not modify it.",
        "Preserve the directory and inspect its evidence manually.", reason,
    )


def _conflict(facts: dict, reason: str, final_output: str) -> RecoveryCandidate:
    return RecoveryCandidate(
        **facts, final_output=final_output, evidence_consistent=False,
        classification="needs_attention", safe_next_action=False,
        summary="Session evidence is incomplete or conflicting — TikREC will not modify it.",
        next_action="Preserve all artifacts and inspect the conflict manually.",
        untouched_reason=reason,
    )


def _output_is_proven(output, values, media_inspector):
    try:
        if output.is_symlink() or not output.is_file() or output.stat().st_size == 0:
            return False
        info = media_inspector(output)
    except Exception:
        return False
    if (info is None or not info.video_codec or not info.format_name
            or type(info.duration_seconds) not in {int, float}
            or not math.isfinite(info.duration_seconds) or info.duration_seconds <= 0):
        return False
    media = values.get("media")
    if not isinstance(media, dict) or not {
        "video_codec", "audio_codec", "width", "height"
    }.issubset(media):
        return False
    return all(
        value is None or getattr(info, name) == value
        for name, value in media.items()
        if name in {"video_codec", "audio_codec", "width", "height"}
    )


def _finalization_state(status: str) -> str:
    return {
        "completed": "complete", "failed": "failed",
        "running": "incomplete", "interrupted": "incomplete",
        "pending": "not_yet_attempted", "not_started": "not_yet_attempted",
        "not_requested": "not_requested",
    }[status]


def _output_state(output: Path | None) -> str:
    return "not_declared" if output is None else "missing"


def _apparent_part_count(directory: Path) -> int:
    try:
        return sum(
            1 for path in directory.iterdir()
            if _PART_NAME.fullmatch(path.name) and path.is_file() and not path.is_symlink()
        )
    except OSError:
        return 0


def _check_recovery_artifacts(directory: Path, values: dict) -> None:
    entries = tuple(directory.iterdir())
    expected = {record["evidence"] for record in recovery_records(values)}
    evidence = {
        path.name for path in entries if path.name.startswith(".tikrec-writer-crash-")
    }
    staging = tuple(
        path for path in entries if path.name.startswith(".tikrec-writer-recovery-")
    )
    if evidence != expected or staging:
        raise ValueError("uncommitted writer recovery artifacts require service evidence")


def safe_source_description(candidate: RecoveryCandidate) -> str:
    """Describe stored source identity without guessing a creator or exposing URLs."""
    labels = {
        "tiktok_live": "TikTok LIVE",
        "direct_flv": "direct media source",
        "tag_stream": "supplied tag stream",
    }
    source = labels.get(candidate.source_type, "unknown")
    if candidate.room_id is not None:
        try:
            return f"{source} (room {canonical_room_id(candidate.room_id)})"
        except ValueError:
            return "unknown"
    return source
