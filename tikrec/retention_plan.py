"""Conservative, read-only age-retention planning for immediate sessions."""

from __future__ import annotations

import math
import os
import re
import time
from collections.abc import Callable
from pathlib import Path

from .configuration import Configuration
from .creator_identity import validate_creator_handle
from .media import MediaInfo, inspect_media
from .recovery_discovery import discover_recovery_candidates, _read_manifest
from .writer_recovery_evidence import recovery_records


def plan_retention(root: Path, configuration: Configuration, *,
                   clock: Callable[[], float] = time.time,
                   media_inspector: Callable[[Path], MediaInfo | None] = inspect_media) -> dict:
    """Classify immediate TikREC session directories without modifying artifacts."""
    configuration.validate()
    scope = Path(root)
    if (str(scope).startswith("\\\\") or any(path.is_symlink() for path in (scope, *scope.parents))
            or not scope.is_dir()):
        raise ValueError("retention root must be a regular local directory")
    scope = scope.resolve(strict=True)
    now = clock()
    if type(now) not in {int, float} or not math.isfinite(now):
        raise ValueError("retention clock must be finite")
    children = sorted((path for path in scope.iterdir()
                       if path.name.lower().endswith(".parts")),
                      key=lambda path: (path.name.casefold(), path.name))
    sessions = [_inspect(path, scope, configuration, now, media_inspector)
                for path in children]
    # A second session claiming one output makes both claims unsafe, even if one is incomplete.
    claims: dict[str, list[dict]] = {}
    identities: dict[str, list[dict]] = {}
    for session in sessions:
        if session["session_id"] is not None:
            identities.setdefault(session["session_id"], []).append(session)
        if session["output_path"] is not None:
            key = os.path.normcase(str(Path(session["output_path"]).resolve()))
            claims.setdefault(key, []).append(session)
    for owners in (*claims.values(), *identities.values()):
        if len(owners) > 1:
            for session in owners:
                session["classification"] = "needs_attention"
                session["reason"] = "evidence_conflict"
    return {"root": str(scope), "retention_max_age_days": configuration.retention_max_age_days,
            "sessions": sessions}


def _inspect(directory, root, config, now, media_inspector):
    item = {"parts_directory": str(directory), "session_id": None,
            "creator": None, "ended_at": None, "output_path": None,
            "classification": "needs_attention", "reason": "evidence_conflict",
            "protected": None}
    if directory.is_symlink() or not directory.is_dir():
        return item
    try:
        manifest_path = directory / "session.json"
        if manifest_path.is_symlink() or not manifest_path.is_file():
            return item
        before = _evidence_stamp(directory)
        values = _read_manifest(manifest_path)
        declared = values.get("output_path")
        # Reject outside/relative declarations before recovery inspection could open them.
        if (type(declared) is not str or not Path(declared).is_absolute()
                or Path(declared) != directory.with_suffix(".mp4")):
            return item
        candidates = discover_recovery_candidates(directory, media_inspector=media_inspector)
        if len(candidates) != 1:
            return item
        candidate = candidates[0]
        if not candidate.evidence_consistent:
            return item
        if _read_manifest(manifest_path) != values:
            return item
        if _unrecognized_evidence(directory, values):
            return item
        after = _evidence_stamp(directory)
        if before != after:
            return item
        item["session_id"] = candidate.session_id
        item["ended_at"] = values.get("ended_at")
        item["output_path"] = candidate.output_path
        if values["source_type"] != "tiktok_live":
            return _mark(item, "ineligible", "source_not_tiktok_live")
        creator = values.get("creator")
        if creator is None:
            return _mark(item, "ineligible", "creator_unknown")
        item["creator"] = validate_creator_handle(creator)
        item["protected"] = creator in config.retention_protected_creators
        if item["protected"]:
            return _mark(item, "protected", "protected_creator")
        if candidate.classification != "complete" or values["status"] != "completed":
            return _mark(item, "ineligible", "session_incomplete")
        output = Path(candidate.output_path)
        # Restrict proof to one regular final output directly inside the selected root.
        if (output.is_symlink() or output.resolve().parent != root
                or output.resolve() != directory.with_suffix(".mp4").resolve()):
            return _mark(item, "needs_attention", "evidence_conflict")
        if config.retention_max_age_days is None:
            return _mark(item, "retained", "retention_disabled")
        if values["ended_at"] <= now - config.retention_max_age_days * 86400:
            return _mark(item, "eligible", "age_threshold_reached")
        return _mark(item, "retained", "not_old_enough")
    except (OSError, ValueError, TypeError, KeyError, AttributeError, OverflowError):
        return _mark(item, "needs_attention", "evidence_conflict")


def _evidence_stamp(directory: Path) -> tuple:
    """Notice changes to immediate evidence while an advisory plan is computed."""
    final_output = directory.with_suffix(".mp4")
    paths = (directory, *directory.iterdir())
    if final_output.exists() or final_output.is_symlink():
        paths += (final_output,)
    return tuple(sorted((path.name, path.lstat().st_mode, path.lstat().st_size,
                         path.lstat().st_mtime_ns, path.lstat().st_ino)
                        for path in paths))


def _unrecognized_evidence(directory: Path, values: dict) -> bool:
    """Do not mark unknown files safe for a future whole-session cleanup."""
    allowed = {"session.json", "connections.jsonl"}
    allowed.update(record["evidence"] for record in recovery_records(values))
    for path in directory.iterdir():
        if path.is_symlink() or not path.is_file():
            return True
        if path.name not in allowed and re.fullmatch(r"part-[0-9]+\.flv", path.name) is None:
            return True
    return False


def _mark(item: dict, classification: str, reason: str) -> dict:
    item["classification"] = classification
    item["reason"] = reason
    return item
