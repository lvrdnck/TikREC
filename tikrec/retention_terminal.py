"""Strict terminal proof used only for advisory retention eligibility."""

from __future__ import annotations

import json
import math
from pathlib import Path

from .session_resume import _timestamp, _unique_values
from .writer_recovery_evidence import recovery_records


def terminal_success(directory: Path, values: dict) -> bool:
    """Require coherent completion and no durable activity after its terminal time."""
    try:
        start, end, elapsed = (values[key] for key in
                               ("started_at", "ended_at", "elapsed_seconds"))
        if (values["status"] != "completed" or values["interrupted"] is not False
                or values["error"] is not None or not isinstance(values["finalization"], dict)
                or values["finalization"]["status"] != "completed"
                or values["finalization"]["error"] is not None
                or not _timestamp(start) or not _timestamp(end) or end < start
                or not _timestamp(elapsed)
                or not math.isclose(elapsed, end - start, rel_tol=1e-9, abs_tol=1e-6)):
            return False
        for record in recovery_records(values):
            if not _within_session(record["timestamp"], start, end):
                return False
        log = directory / "connections.jsonl"
        if log.exists():
            if log.is_symlink() or not log.is_file():
                return False
            with log.open(encoding="utf-8") as handle:
                for line in handle:
                    record = json.loads(line, object_pairs_hook=_unique_values)
                    if record.get("event") is None:
                        if not _at_or_before_end(record["ended_at"], end):
                            return False
                        for field in ("started_at", "resolved_at", "http_opened_at",
                                      "first_media_tag_at", "first_retained_media_at",
                                      "last_retained_media_at"):
                            if (record.get(field) is not None
                                    and not _at_or_before_end(record[field], record["ended_at"])):
                                return False
                    elif not _at_or_before_end(record["timestamp"], end):
                        return False
        return True
    except (OSError, UnicodeError, ValueError, TypeError, KeyError, AttributeError):
        return False


def _within_session(timestamp: object, start: float, end: float) -> bool:
    return _timestamp(timestamp) and start <= timestamp <= end


def _at_or_before_end(timestamp: object, end: float) -> bool:
    return _timestamp(timestamp) and timestamp <= end
