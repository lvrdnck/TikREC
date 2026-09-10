"""Coordinate tag acquisition, part writing, and optional finalization."""

from __future__ import annotations

import json
import os
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

from .finalize import finalize_parts
from .flv import FlvTag
from .source import RawCopy, iter_url_tags
from .writer import PartTiming, write_parts


class CaptureError(RuntimeError):
    """Raised when capture or finalization fails after preserving part files."""

    def __init__(self, message: str, parts: tuple[Path, ...] = ()) -> None:
        super().__init__(message)
        self.parts = parts


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


@dataclass(frozen=True)
class CaptureResult:
    """The completed parts, final output, interruption state, and connections."""

    parts: tuple[Path, ...]
    output_path: Path | None
    interrupted: bool = False
    connections: tuple[ConnectionRecord, ...] = ()


def capture_tags(
    tags: Iterable[FlvTag],
    *,
    parts_directory: Path,
    output_path: Path | None = None,
    writer: Callable[[Iterable[FlvTag], Path], tuple[Path, ...]] = write_parts,
    finalizer: Callable[[Iterable[Path], Path], Path] = finalize_parts,
) -> CaptureResult:
    """Record supplied tags, optionally finalize them, and return their paths."""
    parts_directory = Path(parts_directory)
    output_path = Path(output_path) if output_path is not None else None
    _prepare_session(parts_directory, output_path)
    interrupted = False
    try:
        parts = writer(tags, parts_directory)
    except KeyboardInterrupt:
        interrupted = True
        parts = _completed_parts(parts_directory)
    except Exception as error:
        parts = _completed_parts(parts_directory)
        raise CaptureError(f"capture failed: {error}", parts) from error

    if not parts:
        if interrupted or output_path is None:
            return CaptureResult(parts, None, interrupted)
        raise CaptureError("capture produced no completed FLV parts")
    if output_path is None:
        return CaptureResult(parts, None, interrupted)

    try:
        final_output = finalizer(parts, output_path)
    except KeyboardInterrupt:
        return CaptureResult(parts, None, True)
    except Exception as error:
        raise CaptureError(f"finalization failed: {error}", parts) from error
    return CaptureResult(parts, final_output, interrupted)


def capture_url(
    url: str,
    *,
    parts_directory: Path,
    output_path: Path | None = None,
    tag_source: Callable[[str], Iterable[FlvTag]] = iter_url_tags,
    raw_copy_dir: Path | None = None,
    raw_tag_source: Callable[[str, RawCopy], Iterable[FlvTag]] | None = None,
    warning: Callable[[str], None] | None = None,
    writer: Callable[[Iterable[FlvTag], Path], tuple[Path, ...]] = write_parts,
    finalizer: Callable[[Iterable[Path], Path], Path] = finalize_parts,
) -> CaptureResult:
    """Record one direct FLV URL, optionally retaining its raw HTTP bytes."""
    raw_copy: RawCopy | None = None
    parts: tuple[Path, ...] = ()
    outcome = "closed"
    connection_error: Exception | None = None
    started_at = time.time()

    def source() -> Iterable[FlvTag]:
        nonlocal raw_copy
        if raw_copy_dir is None:
            yield from tag_source(url)
            return
        if raw_tag_source is not None:
            raw_copy = RawCopy(raw_copy_path(raw_copy_dir, 1), warning)
            yield from raw_tag_source(url, raw_copy)
            return
        if tag_source is iter_url_tags:
            raw_copy = RawCopy(raw_copy_path(raw_copy_dir, 1), warning)
            yield from iter_url_tags(url, raw_copy=raw_copy)
            return
        if warning is not None:
            warning("raw copy is unavailable for a custom tag source")
        yield from tag_source(url)

    try:
        result = capture_tags(
            source(),
            parts_directory=parts_directory,
            output_path=output_path,
            writer=writer,
            finalizer=finalizer,
        )
        parts = result.parts
        outcome = "interrupted" if result.interrupted else "closed"
        return result
    except CaptureError as error:
        parts = error.parts
        outcome = "connection_error"
        connection_error = error
        raise
    finally:
        if raw_copy is not None:
            raw_copy.close()
            append_connection_record(
                Path(parts_directory) / "connections.jsonl",
                ConnectionRecord(
                    1,
                    started_at,
                    time.time(),
                    None,
                    parts,
                    outcome,
                    None if connection_error is None else str(connection_error),
                    raw_copy=raw_copy.saved_path,
                ),
            )


def raw_copy_path(directory: Path, connection_number: int) -> Path:
    return Path(directory) / f"connection-{connection_number:04d}.raw"


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
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(values, sort_keys=True) + "\n")
        handle.flush()
        # A process killed between reconnects must not lose the closed record.
        os.fsync(handle.fileno())


def _prepare_session(parts_directory: Path, output_path: Path | None) -> None:
    if parts_directory.exists():
        raise FileExistsError(f"refusing to reuse existing session directory: {parts_directory}")
    if output_path is not None and output_path.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {output_path}")
    parts_directory.mkdir(parents=True)


def _completed_parts(parts_directory: Path) -> tuple[Path, ...]:
    return tuple(sorted(parts_directory.glob("part-*.flv")))
