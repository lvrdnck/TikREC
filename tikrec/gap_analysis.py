"""Read-only reconnect-gap analysis from durable connection evidence."""

from __future__ import annotations

import json
import math
import statistics
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


COMPONENTS = (
    "previous_tail_seconds",
    "local_backoff_seconds",
    "resolution_seconds",
    "http_setup_seconds",
    "initial_media_seconds",
    "keyframe_gate_seconds",
    "total_gap_seconds",
)


@dataclass(frozen=True)
class FailedAttempt:
    """One recorded non-media attempt between media-bearing connections."""

    connection: int
    outcome: str | None
    duration_seconds: float | None


@dataclass(frozen=True)
class ReconnectGap:
    """Measured wall-clock components between adjacent media connections."""

    previous_connection: int
    current_connection: int
    classification: str
    previous_tail_seconds: float | None
    local_backoff_seconds: float | None
    resolution_seconds: float | None
    http_setup_seconds: float | None
    initial_media_seconds: float | None
    keyframe_gate_seconds: float | None
    total_gap_seconds: float | None
    intervening_attempts: tuple[FailedAttempt, ...]
    unrecorded_attempt_count: int
    boundary_events: tuple[str, ...]


@dataclass(frozen=True)
class ComponentSummary:
    """Available observations for one reconnect-gap component."""

    count: int
    median_seconds: float | None
    minimum_seconds: float | None
    maximum_seconds: float | None


def read_connection_log(path: Path) -> tuple[dict[str, Any], ...]:
    """Read JSONL evidence without modifying or resolving any recording artifact."""
    records: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            try:
                value = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"invalid JSON on line {line_number}") from error
            if not isinstance(value, dict):
                raise ValueError(f"connection log line {line_number} is not an object")
            records.append(value)
    return tuple(records)


def analyze_connection_log(path: Path) -> tuple[ReconnectGap, ...]:
    """Calculate gaps between adjacent media-bearing connections in one log."""
    return analyze_records(read_connection_log(path))


def boundary_events(records: tuple[dict[str, Any], ...]) -> tuple[str, ...]:
    """List explicit lifecycle/recovery boundaries, including terminal ones."""
    return tuple(_event_label(record) for record in records if record.get("event") is not None)


def analyze_records(records: tuple[dict[str, Any], ...]) -> tuple[ReconnectGap, ...]:
    """Calculate reconnect gaps while retaining intervening attempts and boundaries."""
    media = [(index, record) for index, record in enumerate(records) if _media_record(record)]
    gaps: list[ReconnectGap] = []
    for (previous_index, previous), (current_index, current) in zip(media, media[1:]):
        bridge = records[previous_index + 1:current_index]
        attempts = tuple(_failed_attempt(record) for record in bridge if _connection_record(record))
        events = tuple(_event_label(record) for record in bridge if record.get("event") is not None)
        previous_number = _connection_number(previous)
        current_number = _connection_number(current)
        allocated_between = max(0, current_number - previous_number - 1)
        recorded_numbers = {attempt.connection for attempt in attempts}
        unrecorded = max(0, allocated_between - len(recorded_numbers))
        gaps.append(ReconnectGap(
            previous_connection=previous_number,
            current_connection=current_number,
            classification=_classify(previous, events, unrecorded),
            previous_tail_seconds=_difference(previous, "ended_at", previous, "last_retained_media_at"),
            local_backoff_seconds=_difference(current, "started_at", previous, "ended_at"),
            resolution_seconds=_difference(current, "resolved_at", current, "started_at"),
            http_setup_seconds=_difference(current, "http_opened_at", current, "resolved_at"),
            initial_media_seconds=_difference(current, "first_media_tag_at", current, "http_opened_at"),
            keyframe_gate_seconds=_difference(
                current, "first_retained_media_at", current, "first_media_tag_at"
            ),
            total_gap_seconds=_difference(
                current, "first_retained_media_at", previous, "last_retained_media_at"
            ),
            intervening_attempts=attempts,
            unrecorded_attempt_count=unrecorded,
            boundary_events=events,
        ))
    return tuple(gaps)


def summarize_gaps(
    gaps: tuple[ReconnectGap, ...], *, classification: str = "ordinary"
) -> dict[str, ComponentSummary]:
    """Summarize available component values without replacing unknowns with zero."""
    selected = [gap for gap in gaps if gap.classification == classification]
    summary: dict[str, ComponentSummary] = {}
    for component in COMPONENTS:
        values = [getattr(gap, component) for gap in selected]
        available = [value for value in values if value is not None]
        summary[component] = ComponentSummary(
            count=len(available),
            median_seconds=statistics.median(available) if available else None,
            minimum_seconds=min(available) if available else None,
            maximum_seconds=max(available) if available else None,
        )
    return summary


def gap_as_dict(gap: ReconnectGap) -> dict[str, Any]:
    """Return a JSON-serializable reconnect result for diagnostic scripts."""
    return asdict(gap)


def _media_record(record: dict[str, Any]) -> bool:
    return (_connection_record(record)
            and _number(record.get("first_retained_media_at")) is not None
            and _number(record.get("last_retained_media_at")) is not None)


def _connection_record(record: dict[str, Any]) -> bool:
    return record.get("event") is None and _integer(record.get("connection")) is not None


def _connection_number(record: dict[str, Any]) -> int:
    number = _integer(record.get("connection"))
    if number is None:
        raise ValueError("media connection has no positive connection number")
    return number


def _failed_attempt(record: dict[str, Any]) -> FailedAttempt:
    return FailedAttempt(
        connection=_connection_number(record),
        outcome=record.get("outcome") if isinstance(record.get("outcome"), str) else None,
        duration_seconds=_difference(record, "ended_at", record, "started_at"),
    )


def _difference(
    later_record: dict[str, Any], later_field: str,
    earlier_record: dict[str, Any], earlier_field: str,
) -> float | None:
    later = _number(later_record.get(later_field))
    earlier = _number(earlier_record.get(earlier_field))
    return None if later is None or earlier is None else later - earlier


def _number(value: object) -> float | None:
    if type(value) not in {int, float} or not math.isfinite(value):
        return None
    return float(value)


def _integer(value: object) -> int | None:
    return value if type(value) is int and value > 0 else None


def _event_label(record: dict[str, Any]) -> str:
    event = str(record.get("event"))
    detail = record.get("reason") if event in {"capture_resume", "service_recovery"} else record.get("phase")
    return event if not isinstance(detail, str) else f"{event}:{detail}"


def _classify(previous: dict[str, Any], events: tuple[str, ...], unrecorded: int) -> str:
    if any(event.startswith("service_recovery:process_restart") for event in events):
        return "service_restart"
    if any(event.startswith("capture_resume") for event in events):
        return "explicit_resume"
    if any(event.startswith("network_recovery") for event in events):
        return "network_recovery"
    if any(event.startswith("room_status") for event in events):
        return "room_end_confirmation"
    if any(event.startswith("service_recovery") for event in events):
        return "service_recovery"
    if previous.get("outcome") in {"connection_error", "stalled"}:
        return "network_recovery"
    if unrecorded:
        return "other_recovery"
    return "ordinary" if previous.get("outcome") == "closed" else "other_recovery"
