"""Conservative, read-only age-retention planning for immediate sessions."""

from __future__ import annotations

import math
import json
import re
import time
from collections.abc import Callable
from pathlib import Path

from .configuration import Configuration
from .creator_identity import validate_creator_handle
from .media import MediaInfo, inspect_media
from .recovery_discovery import discover_recovery_candidates
from .session_resume import _unique_values
from .writer_recovery_evidence import recovery_records
from .retention_paths import local_path
from .retention_locality import LocalVolume, local_volume, proven_local
from .retention_snapshot import (ObservedInstability, capture_claim, capture_root,
                                 checked_control)
from .retention_terminal import terminal_success


def plan_retention(root: Path, configuration: Configuration, *,
                   clock: Callable[[], float] = time.time,
                   media_inspector: Callable[[Path], MediaInfo | None] = inspect_media) -> dict:
    """Classify immediate TikREC session directories without modifying artifacts."""
    configuration.validate()
    scope = local_path(Path(root), directory=True)
    if not proven_local(scope):
        raise ValueError("retention root locality could not be proven")
    volume = local_volume(scope)
    if volume is None:
        raise ValueError("retention root volume could not be proven")
    now = clock()
    if type(now) not in {int, float} or not math.isfinite(now):
        raise ValueError("retention clock must be finite")
    initial = capture_root(scope, _claims)
    sessions, unknown = [], not initial.stable or any(
        claim.uncertain for claim in initial.claims)
    for claim in initial.claims:
        try:
            item = _inspect(claim, scope, volume, configuration, now, media_inspector)
        except ObservedInstability:
            unknown = True
            item = _empty_item(Path(claim.directory))
        if ((item["session_id"] is not None and item["session_id"] != claim.session_id)
                or (item["output_path"] is not None and item["output_path"] != claim.output_path)):
            unknown = True
        item["session_id"], item["output_path"] = claim.session_id, claim.output_path
        sessions.append(item)
    # A late child, replacement, or changed control claim invalidates the whole plan.
    try:
        final = capture_root(scope, _claims)
        unknown |= not final.stable or final != initial
    except (OSError, ValueError, TypeError):
        unknown = True
    claims: dict[tuple, list[int]] = {}
    for index, claim in enumerate(initial.claims):
        for kind, value in (("session", claim.session_id), ("lexical", claim.output_key),
                            ("physical", claim.physical_output)):
            if value is not None:
                claims.setdefault((kind, value), []).append(index)
    for owners in claims.values():
        if len(owners) > 1:
            for index in owners:
                sessions[index]["classification"] = "needs_attention"
                sessions[index]["reason"] = "evidence_conflict"
    # An unreadable immediate claimant could alias any output or UUID in this root.
    if unknown:
        for session in sessions:
            session["classification"] = "needs_attention"
            session["reason"] = "evidence_conflict"
    return {"root": str(scope), "retention_max_age_days": configuration.retention_max_age_days,
            "sessions": sessions}


def _inspect(claim, root, volume, config, now, media_inspector):
    directory = Path(claim.directory)
    item = _empty_item(directory)
    try:
        local_path(directory, directory=True)
        _artifact_scope(directory, volume)
        manifest_path = directory / "session.json"
        control = lambda path: checked_control(claim, path)
        before = _evidence_stamp(directory)
        content = control(manifest_path)
        if content is None:
            return item
        values = json.loads(content.decode("utf-8"), object_pairs_hook=_unique_values)
        declared = values.get("output_path")
        # Reject outside/relative declarations before recovery inspection could open them.
        if (type(declared) is not str or not Path(declared).is_absolute()
                or Path(declared) != directory.with_suffix(".mp4")):
            return item
        # Recovery inspection may open the final output; reject redirects first.
        output = directory.with_suffix(".mp4")
        if output.exists() or output.is_symlink():
            local_path(output, directory=False)
        candidates = discover_recovery_candidates(
            directory, media_inspector=media_inspector, control_reader=control)
        if len(candidates) != 1:
            return item
        candidate = candidates[0]
        if not candidate.evidence_consistent:
            return item
        if control(manifest_path) != content:
            return item
        if _unrecognized_evidence(directory, values):
            return item
        try:
            after = _evidence_stamp(directory)
        except (OSError, ValueError) as error:
            raise ObservedInstability("observed candidate evidence became unreadable") from error
        if before != after:
            raise ObservedInstability("observed candidate evidence changed")
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
        log = control(directory / "connections.jsonl")
        if candidate.classification != "complete" or not terminal_success(
                directory, values, connections_bytes=b"" if log is None else log):
            return _mark(item, "ineligible", "session_incomplete")
        output = Path(candidate.output_path)
        # Restrict proof to one regular final output directly inside the selected root.
        if (local_path(output, directory=False).parent != root
                or output != directory.with_suffix(".mp4")):
            return _mark(item, "needs_attention", "evidence_conflict")
        if config.retention_max_age_days is None:
            return _mark(item, "retained", "retention_disabled")
        if values["ended_at"] <= now - config.retention_max_age_days * 86400:
            _checked_stamp(directory, after)
            if (control(manifest_path) != content
                    or control(directory / "connections.jsonl") != log):
                raise ObservedInstability("observed candidate evidence changed")
            return _mark(item, "eligible", "age_threshold_reached")
        return _mark(item, "retained", "not_old_enough")
    except ObservedInstability:
        raise
    except (OSError, ValueError, TypeError, KeyError, AttributeError, OverflowError):
        return _mark(item, "needs_attention", "evidence_conflict")


def _empty_item(directory: Path) -> dict:
    return {"parts_directory": str(directory), "session_id": None,
            "creator": None, "ended_at": None, "output_path": None,
            "classification": "needs_attention", "reason": "evidence_conflict",
            "protected": None}


def _claims(directory: Path, root: Path):
    """Return an immutable bounded claim independent of eligibility."""
    return capture_claim(directory, root)


def _artifact_scope(directory: Path, volume: LocalVolume) -> None:
    """Prove every immediate artifact is unredirected on the root's local volume."""
    for path in (directory, *directory.iterdir()):
        local_path(path, directory=path == directory)
        if not proven_local(path) or local_volume(path) != volume:
            raise ValueError("retention artifact is outside the proven local volume")
    output = directory.with_suffix(".mp4")
    if output.exists() or output.is_symlink():
        local_path(output, directory=False)
        if not proven_local(output) or local_volume(output) != volume:
            raise ValueError("retention output is outside the proven local volume")


def _evidence_stamp(directory: Path) -> tuple:
    """Notice changes to immediate evidence while an advisory plan is computed."""
    final_output = directory.with_suffix(".mp4")
    paths = (directory, *directory.iterdir())
    if final_output.exists() or final_output.is_symlink():
        paths += (final_output,)
    return tuple(sorted((path.name, path.lstat().st_mode, path.lstat().st_size,
                         path.lstat().st_mtime_ns, path.lstat().st_ino)
                        for path in paths))


def _checked_stamp(directory: Path, expected: tuple) -> None:
    """Escalate an observed candidate identity loss beyond that one candidate."""
    try:
        current = _evidence_stamp(directory)
    except (OSError, ValueError) as error:
        raise ObservedInstability("observed candidate evidence became unreadable") from error
    if current != expected:
        raise ObservedInstability("observed candidate evidence changed")


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
