"""Retention-only chronological proof over validated durable connection evidence."""

from __future__ import annotations

import json
from io import StringIO
from pathlib import Path

from .session_resume import _timestamp, _unique_values


_MILESTONES = ("resolved_at", "http_opened_at", "first_media_tag_at",
               "first_retained_media_at", "last_retained_media_at")
_OUTAGE_ENDS = {"recovered", "exhausted", "offline", "live_changed", "user_stop", "failed"}


def coherent_chronology(directory: Path, started: float, ended: float,
                        *, connections_bytes: bytes | None = None) -> bool:
    """Require session, connection, resume, and outage order before retention."""
    path = directory / "connections.jsonl"
    if connections_bytes is None and not path.exists() and not path.is_symlink():
        return True
    if connections_bytes is None and (path.is_symlink() or not path.is_file()):
        return False
    try:
        previous_end = None
        latest_recorded = 0
        pending_resumes: dict[int, float] = {}
        outage = None
        handle = (StringIO(connections_bytes.decode("utf-8")) if connections_bytes is not None
                  else path.open(encoding="utf-8"))
        first_resolution = False
        with handle:
            for line in handle:
                record = json.loads(line, object_pairs_hook=_unique_values)
                event = record.get("event")
                if event is None:
                    opened, closed = record["started_at"], record["ended_at"]
                    if (not _timestamp(opened) or not _timestamp(closed)
                            or opened > closed or closed > ended
                            or (previous_end is not None and opened < previous_end)
                            or closed < latest_recorded):
                        return False
                    if opened < started and not first_resolution:
                        # Resolver-only failures can precede the first real session.
                        resolved = record.get("resolved_at")
                        media = any(record.get(field) is not None for field in
                                    _MILESTONES[1:])
                        if (resolved is None and not media and closed <= started
                                and record.get("outcome") == "resolver_error"
                                and record.get("part_start") is None
                                and record.get("part_end") is None
                                and not record.get("part_timings")
                                and record.get("raw_copy") is None
                                and record.get("raw_arrivals") is None):
                            pass
                        elif (not _timestamp(resolved)
                              or not opened <= resolved <= started <= closed
                              or record.get("outcome") == "resolver_error"
                              or any(record.get(field) is not None and
                                     record[field] < started for field in _MILESTONES[1:])):
                            return False
                        else:
                            first_resolution = True
                    elif opened < started:
                        return False
                    elif not first_resolution:
                        first_resolution = True
                    if not _milestones(record, opened, closed):
                        return False
                    boundary = pending_resumes.pop(record["connection"], None)
                    if boundary is not None and boundary > opened:
                        return False
                    previous_end, latest_recorded = closed, closed
                    continue
                timestamp = record["timestamp"]
                if (not _timestamp(timestamp) or not started <= timestamp <= ended
                        or timestamp < latest_recorded):
                    return False
                if event == "capture_resume":
                    pending_resumes[record["connection"]] = timestamp
                elif event == "network_recovery":
                    phase = record["phase"]
                    progress = (record["retry_attempt"], record["outage_elapsed_seconds"])
                    # Monotonic outage duration cannot exceed this session's wall
                    # interval; one second allows separate clock-call ordering.
                    if progress[1] > timestamp - started + 1:
                        return False
                    if phase == "entered":
                        if outage is not None:
                            return False
                        outage = (timestamp, *progress)
                    elif phase in _OUTAGE_ENDS:
                        if (outage is None or progress[0] < outage[1]
                                or progress[1] < outage[2]
                                or progress[1] > timestamp - outage[0] + outage[2] + 1):
                            return False
                        outage = None
                    else:
                        return False
                elif event not in {"room_status", "service_recovery"}:
                    return False
                latest_recorded = timestamp
        return not pending_resumes and outage is None
    except (OSError, UnicodeError, ValueError, TypeError, KeyError, AttributeError):
        return False


def _milestones(record: dict, opened: float, closed: float) -> bool:
    previous = opened
    for field in _MILESTONES:
        timestamp = record.get(field)
        if timestamp is not None:
            if not _timestamp(timestamp) or not previous <= timestamp <= closed:
                return False
            previous = timestamp
    return True
