"""Observe source timestamp replays without changing retained tags."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from .flv import FlvTag

if TYPE_CHECKING:
    from .writer import _OpenPart


@dataclass(frozen=True)
class TimestampReplay:
    """A completed source timestamp replay retained in one FLV part.

    ``position`` is the one-based ordinal of the first backward tag in the
    retained part. ``recovered`` is false when the part ended before source
    timestamps passed the point immediately before the backward jump.
    """

    path: Path
    position: int
    previous_timestamp: int
    timestamp: int
    magnitude: int
    replayed_tag_count: int
    recovered: bool


@dataclass(frozen=True)
class PartTiming:
    """Source timestamps and optional codec/metadata facts for a completed part.

    ``configuration_timestamp`` is diagnostic-only: live FLV sequence headers
    are commonly timestamped zero even when media uses a later clock origin.
    """

    path: Path
    configuration_timestamp: int
    first_media_timestamp: int
    first_keyframe_timestamp: int
    last_tag_timestamp: int
    timestamp_replays: tuple[TimestampReplay, ...] = ()
    width: int | None = None
    height: int | None = None
    nominal_frame_rate: str | None = None
    nominal_frame_rate_source: str | None = None

    @property
    def keyframe_gate_duration(self) -> int:
        """Return the source-time media interval withheld until a keyframe."""
        return self.first_keyframe_timestamp - self.first_media_timestamp


@dataclass
class _PendingTimestampReplay:
    position: int
    previous_timestamp: int
    timestamp: int
    replayed_tag_count: int = 1


def _observe_timestamp(
    part: _OpenPart,
    tag: FlvTag,
    callback: Callable[[TimestampReplay], None] | None,
) -> None:
    stream = tag.tag_type
    replay = part.pending_replays.get(stream)
    if replay is not None:
        if tag.timestamp <= replay.previous_timestamp:
            replay.replayed_tag_count += 1
            return
        _finish_timestamp_replay(part, stream, recovered=True, callback=callback)

    previous = part.last_observed_timestamps.get(stream)
    if previous is not None and tag.timestamp < previous:
        part.pending_replays[stream] = _PendingTimestampReplay(
            part.tag_position,
            previous,
            tag.timestamp,
        )
        return
    part.last_observed_timestamps[stream] = tag.timestamp


def _finish_timestamp_replay(
    part: _OpenPart,
    stream: int,
    *,
    recovered: bool,
    callback: Callable[[TimestampReplay], None] | None,
) -> None:
    replay = part.pending_replays.pop(stream, None)
    if replay is None:
        return
    event = TimestampReplay(
        part.final_path,
        replay.position,
        replay.previous_timestamp,
        replay.timestamp,
        replay.previous_timestamp - replay.timestamp,
        replay.replayed_tag_count,
        recovered,
    )
    part.timestamp_replays.append(event)
    if callback is not None:
        callback(event)
