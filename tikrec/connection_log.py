"""Serialize durable connection and room-status evidence."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from .writer import PartTiming


@dataclass(frozen=True)
class ConnectionRecord:
    """One closed live connection and the retained parts it produced."""

    number: int
    started_at: float
    ended_at: float
    gap_before: float | None
    parts: tuple[Path, ...]
    outcome: str
    error: str | None = None
    part_timings: tuple[PartTiming, ...] = ()
    raw_copy: Path | None = None


def append_connection_record(path: Path, record: ConnectionRecord) -> None:
    """Append one durable connection record, including any successful raw copy."""
    values = {
        "connection": record.number,
        "started_at": record.started_at,
        "ended_at": record.ended_at,
        "gap_before": record.gap_before,
        "part_start": record.parts[0].name if record.parts else None,
        "part_end": record.parts[-1].name if record.parts else None,
        "part_timings": [
            {
                "name": timing.path.name,
                "configuration_timestamp": timing.configuration_timestamp,
                "first_media_timestamp": timing.first_media_timestamp,
                "first_keyframe_timestamp": timing.first_keyframe_timestamp,
                "keyframe_gate_duration": timing.keyframe_gate_duration,
                "last_tag_timestamp": timing.last_tag_timestamp,
                "timestamp_replays": [
                    {
                        "position": replay.position,
                        "previous_timestamp": replay.previous_timestamp,
                        "timestamp": replay.timestamp,
                        "magnitude": replay.magnitude,
                        "replayed_tag_count": replay.replayed_tag_count,
                        "recovered": replay.recovered,
                    }
                    for replay in timing.timestamp_replays
                ],
            }
            for timing in record.part_timings
        ],
        "outcome": record.outcome,
        "error": record.error,
        "raw_copy": None if record.raw_copy is None else record.raw_copy.name,
    }
    _append_jsonl_record(path, values)


def append_room_status_record(
    path: Path,
    timestamp: float,
    status: object,
    confirmation_reached: bool,
) -> None:
    """Append durable evidence from a room-status confirmation response."""
    _append_jsonl_record(path, {
        "event": "room_status",
        "timestamp": timestamp,
        "status": status,
        "confirmation_reached": confirmation_reached,
    })


def _append_jsonl_record(path: Path, values: dict[str, object]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(values, sort_keys=True) + "\n")
        handle.flush()
        # A killed process must not lose the last connection or room-status evidence.
        os.fsync(handle.fileno())

