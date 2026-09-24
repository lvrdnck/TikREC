"""Strict terminal proof used only for advisory retention eligibility."""

from __future__ import annotations

import math
from pathlib import Path

from .session_resume import _timestamp
from .retention_chronology import coherent_chronology
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
        return coherent_chronology(directory, start, end)
    except (OSError, UnicodeError, ValueError, TypeError, KeyError, AttributeError):
        return False


def _within_session(timestamp: object, start: float, end: float) -> bool:
    return _timestamp(timestamp) and start <= timestamp <= end
