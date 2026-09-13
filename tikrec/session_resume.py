"""Read-only preflight for explicit continuation of a retained media session."""

from __future__ import annotations

import json
import math
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .finalize import _temporary_output_path
from .manifest import SCHEMA_VERSION, SessionManifest
from .media import MediaInfo, inspect_media
from .session_parts import RetainedParts, discover_parts, part_index
from .tiktok_identity import canonical_room_id


@dataclass(frozen=True)
class ResumeSession:
    """Validated retained media and evidence for the next supplied FLV connection."""

    manifest: SessionManifest
    retained: RetainedParts
    session_id: str
    previous_status: str
    next_connection: int
    previous_end: float | None


def prepare_resume(
    parts_directory: Path, *, output_path: Path | None = None,
    session_id: str | None = None, source_type: str | None = None,
    clock: Callable[[], float] = time.time,
    media_inspector: Callable[[Path], MediaInfo | None] = inspect_media,
) -> ResumeSession:
    """Validate storage/manifest/log without writing, resolving, or repairing anything."""
    directory = Path(parts_directory)
    retained = discover_parts(directory)
    path = directory / "session.json"
    if not path.is_file() or path.is_symlink():
        raise ValueError("resume requires a supported regular session manifest")
    try:
        values = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_values)
        _validate_manifest(values, directory, retained, session_id, source_type)
        _check_output(values.get("output_path"), output_path)
        count, previous_end = _read_connections(directory, retained, values["session_id"])
        if values["status"] != "recording" and count > values["connection_count"]:
            raise ValueError("closed manifest predates newer connection evidence")
        manifest = SessionManifest.load(path, clock=clock, media_inspector=media_inspector)
        # Detect a changed read rather than validate one document and reopen another.
        if manifest is None or manifest.snapshot() != values:
            raise ValueError("session manifest changed during resume preflight")
    except (OSError, UnicodeError, ValueError, TypeError, KeyError, AttributeError, OverflowError) as error:
        raise ValueError("invalid or conflicting resume session; preserve artifacts") from error
    return ResumeSession(manifest, retained, values["session_id"], values["status"],
                         max(values["connection_count"], count) + 1, previous_end)


def _validate_manifest(values, directory, retained, expected_id, expected_type):
    if not isinstance(values, dict):
        raise ValueError("manifest must be an object")
    if type(values.get("schema_version")) is not int or values["schema_version"] != SCHEMA_VERSION:
        raise ValueError("unsupported manifest schema")
    identity = values["session_id"]
    if not isinstance(identity, str) or str(uuid.UUID(identity)) != identity:
        raise ValueError("invalid session identity")
    if expected_id is not None and identity != expected_id:
        raise ValueError("conflicting requested session identity")
    source_type = values["source_type"]
    if source_type not in {"tag_stream", "direct_flv", "tiktok_live"}:
        raise ValueError("unsupported session source type")
    if expected_type is not None and source_type != expected_type:
        raise ValueError("conflicting requested source type")
    if values["status"] not in {"recording", "interrupted", "failed"}:
        raise ValueError("session capture is already terminal or unsupported")
    stored_directory = values["parts_directory"]
    if not isinstance(stored_directory, str) or Path(stored_directory).resolve() != directory.resolve():
        raise ValueError("manifest declares a different parts directory")
    count = values["part_count"]
    if not _count(count) or count > len(retained.parts):
        raise ValueError("manifest declares missing parts")
    # A killed writer can promote before its capture callback updates a recording manifest.
    if count != len(retained.parts) and values["status"] != "recording":
        raise ValueError("closed manifest part count disagrees with retained media")
    connections = values["connection_count"]
    if not _count(connections) or values["reconnect_count"] != max(0, connections - 1):
        raise ValueError("invalid manifest connection counts")
    if not _count(values["reconnect_count"]):
        raise ValueError("invalid manifest reconnect count")
    if not _timestamp(values["started_at"]):
        raise ValueError("invalid original start time")
    ended = values["ended_at"]
    if ended is not None and (not _timestamp(ended) or ended < values["started_at"]):
        raise ValueError("invalid end time")
    if values["status"] == "recording" and ended is not None:
        raise ValueError("recording manifest declares a closed capture")
    if values["status"] != "recording" and ended is None:
        raise ValueError("closed capture lacks an end time")
    if type(values["interrupted"]) is not bool or type(values["recovery_performed"]) is not bool:
        raise ValueError("invalid interruption evidence")
    if values["status"] == "interrupted" and not values["interrupted"]:
        raise ValueError("conflicting interruption evidence")
    if values["finalization"]["status"] not in {"pending", "not_started", "not_requested"}:
        raise ValueError("finalization must be reconciled separately before capture resume")
    room_id = values.get("room_id")
    if room_id is not None and canonical_room_id(room_id) != room_id:
        raise ValueError("invalid stored public room identity")


def _check_output(declared, requested):
    if declared is not None and (not isinstance(declared, str) or not declared
                                 or "\x00" in declared or "://" in declared):
        raise ValueError("invalid declared output")
    declared = Path(declared) if declared is not None else None
    if declared is not None and not declared.suffix:
        raise ValueError("declared output lacks a container suffix")
    requested = Path(requested) if requested is not None else None
    if declared is not None and requested is not None and declared.resolve() != requested.resolve():
        raise ValueError("resume output conflicts with the original declaration")
    for output in {declared, requested} - {None}:
        # Even capture-only resume must not extend media behind an already completed output.
        temporary = _temporary_output_path(output)
        if output.exists() or output.is_symlink() or temporary.exists() or temporary.is_symlink():
            raise ValueError("existing final output or finalizer partial blocks resume")
    if requested is not None and (not requested.suffix or not requested.parent.is_dir()):
        raise ValueError("requested output requires an existing parent and container suffix")


def _read_connections(directory, retained, identity):
    path = directory / "connections.jsonl"
    if not path.exists() and not path.is_symlink():
        return 0, None
    if not path.is_file() or path.is_symlink():
        raise ValueError("connection evidence must be a regular file")
    logged = reserved = 0
    previous_end = None
    claimed_parts = set()
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            # Appending to a crash-truncated JSON line would destroy the evidence boundary.
            if not line.endswith("\n"):
                raise ValueError("incomplete connection log")
            record = json.loads(line, object_pairs_hook=_unique_values)
            if not isinstance(record, dict):
                raise ValueError("malformed connection record")
            event = record.get("event")
            if event == "room_status":
                if (not _timestamp(record["timestamp"]) or "status" not in record or
                        type(record["confirmation_reached"]) is not bool):
                    raise ValueError("malformed room-status evidence")
                continue
            number = record["connection"]
            if not _count(number) or number < 1:
                raise ValueError("invalid connection number")
            if event == "capture_resume":
                if record["session_id"] != identity or number <= max(logged, reserved):
                    raise ValueError("conflicting resume evidence")
                if (not _timestamp(record["timestamp"]) or record["reason"] != "explicit_resume"
                        or record["previous_status"] not in {"recording", "interrupted", "failed"}):
                    raise ValueError("malformed resume boundary evidence")
                index = record["next_part_index"]
                if not _count(index) or not 1 <= index <= retained.next_index:
                    raise ValueError("invalid resume part boundary")
                reserved = number
                continue
            if event is not None or number <= logged or number < reserved:
                raise ValueError("conflicting connection sequence")
            if not _timestamp(record["ended_at"]):
                raise ValueError("invalid connection end time")
            start, end = record.get("part_start"), record.get("part_end")
            if start is not None or end is not None:
                if Path(start).name != start or Path(end).name != end:
                    raise ValueError("connection part references must be bare canonical names")
                first, last = part_index(Path(start)), part_index(Path(end))
                if not 1 <= first <= last < retained.next_index:
                    raise ValueError("connection refers to missing retained parts")
                claimed = set(range(first, last + 1))
                if claimed_parts & claimed:
                    raise ValueError("multiple connections claim the same retained part")
                claimed_parts.update(claimed)
            for timing in record.get("part_timings", []):
                if Path(timing["name"]).name != timing["name"]:
                    raise ValueError("part timing must name a retained file without directory traversal")
                index = part_index(Path(timing["name"]))
                if start is None or not first <= index <= last:
                    raise ValueError("part timing conflicts with the retained connection range")
            logged, previous_end = number, record["ended_at"]
    return max(logged, reserved), previous_end


def _unique_values(pairs):
    values = {}
    for name, value in pairs:
        if name in values:
            raise ValueError("duplicate session evidence fields")
        values[name] = value
    return values


def _count(value):
    return type(value) is int and value >= 0


def _timestamp(value):
    return type(value) in {int, float} and math.isfinite(value) and value >= 0
