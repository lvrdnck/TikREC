"""Reconnect public TikTok LIVE capture without changing direct-FLV capture."""

from __future__ import annotations

import json
import os
import re
import time
from collections.abc import Callable, Iterable
from http.client import HTTPException
from pathlib import Path

from .capture import CaptureError, CaptureResult, ConnectionRecord, _prepare_session
from .finalize import finalize_parts
from .flv import FlvTag
from .source import iter_url_tags
from .tiktok import (
    TikTokOfflineError,
    TikTokResolutionError,
    TikTokResolutionTransientError,
    resolve_live_url,
)
from .writer import PartTiming, write_parts


_URL_PATTERN = re.compile(r"https?://\S+")


def capture_live(
    url: str,
    *,
    parts_directory: Path,
    output_path: Path | None = None,
    resolver: Callable[[str], str] = resolve_live_url,
    tag_source: Callable[[str], Iterable[FlvTag]] = iter_url_tags,
    writer: Callable[..., tuple[Path, ...]] = write_parts,
    finalizer: Callable[[Iterable[Path], Path], Path] = finalize_parts,
    max_consecutive_failures: int = 3,
    max_consecutive_empty_connections: int = 3,
    backoff_seconds: float = 1.0,
    sleeper: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.time,
    progress: Callable[[str], None] | None = None,
    heartbeat: Callable[[Path, int], None] | None = None,
) -> CaptureResult:
    """Record a public LIVE page through reconnects until room-info says offline.

    ``resolver`` and ``tag_source`` are injectable so network behaviour can be
    tested without contacting TikTok. ``progress`` receives safe user-facing
    status messages and ``heartbeat`` receives active-part byte updates. Only
    resolver transport failures and direct-stream connection failures retry.
    """
    _validate_limits(
        max_consecutive_failures,
        max_consecutive_empty_connections,
        backoff_seconds,
    )
    parts_directory = Path(parts_directory)
    output_path = Path(output_path) if output_path is not None else None
    _prepare_session(parts_directory, output_path)

    records: list[ConnectionRecord] = []
    all_parts: list[Path] = []
    next_part_index = 1
    consecutive_failures = 0
    consecutive_empty = 0
    connection_number = 0
    previous_end: float | None = None

    while True:
        connection_number += 1
        started_at = clock()
        connection_parts: list[Path] = []
        part_timings: list[PartTiming] = []

        def retained(path: Path) -> None:
            # This callback preserves a part even when Ctrl-C interrupts writer.
            connection_parts.append(path)

        def part_closed(timing: PartTiming) -> None:
            part_timings.append(timing)

        def part_started(path: Path) -> None:
            _report(progress, f"part started: {path.name}")

        def close_record(outcome: str, error: Exception | None = None) -> ConnectionRecord:
            nonlocal previous_end, next_part_index
            ended_at = clock()
            record = ConnectionRecord(
                connection_number,
                started_at,
                ended_at,
                None if previous_end is None else started_at - previous_end,
                tuple(connection_parts),
                outcome,
                None if error is None else str(error),
                tuple(part_timings),
            )
            _append_connection_record(parts_directory / "connections.jsonl", record)
            records.append(record)
            all_parts.extend(connection_parts)
            # This advances from writer output, rather than inspecting the directory.
            next_part_index += len(connection_parts)
            previous_end = ended_at
            return record

        try:
            _report(progress, "resolving room")
            direct_url = resolver(url)
            _report(progress, f"connection {connection_number} opened")
            written_parts = writer(
                tag_source(direct_url),
                parts_directory,
                start_index=next_part_index,
                on_part_started=part_started,
                on_progress=heartbeat,
                on_part_retained=retained,
                on_part_closed=part_closed,
            )
            # Custom writers may not use the callback, while the built-in writer does.
            if not connection_parts:
                connection_parts.extend(written_parts)
        except KeyboardInterrupt:
            close_record("interrupted")
            if all_parts:
                return _finalize(
                    all_parts,
                    output_path,
                    finalizer,
                    tuple(records),
                    parts_directory,
                    progress,
                    interrupted=True,
                )
            return CaptureResult(tuple(all_parts), None, True, tuple(records))
        except TikTokOfflineError as error:
            close_record("offline", error)
            _report(progress, "room ended")
            if not all_parts:
                raise CaptureError("TikTok account or room is not live") from error
            return _finalize(
                all_parts, output_path, finalizer, tuple(records), parts_directory, progress
            )
        except TikTokResolutionTransientError as error:
            close_record("resolver_error", error)
            consecutive_failures += 1
            reconnect_reason = _safe_reason(error)
        # HTTP reads raise HTTPException (not OSError) when a CDN body ends early.
        except (OSError, EOFError, HTTPException) as error:
            close_record("connection_error", error)
            consecutive_failures += 1
            reconnect_reason = _safe_reason(error)
        except TikTokResolutionError as error:
            close_record("resolution_error", error)
            raise CaptureError(
                f"TikTok LIVE resolution failed: {_safe_reason(error)}", tuple(all_parts)
            ) from error
        except Exception as error:
            close_record("capture_error", error)
            raise CaptureError(f"live capture failed: {_safe_reason(error)}", tuple(all_parts)) from error
        else:
            close_record("closed")
            consecutive_failures = 0
            consecutive_empty = consecutive_empty + 1 if not written_parts else 0
            reconnect_reason = "connection closed"
            if consecutive_empty >= max_consecutive_empty_connections:
                raise CaptureError(
                    "live capture stopped after consecutive connections with no media",
                    tuple(all_parts),
                )

        if consecutive_failures >= max_consecutive_failures:
            raise CaptureError(
                "live capture stopped after consecutive connection failures",
                tuple(all_parts),
            )
        # Re-resolving after every close gets a fresh signed CDN URL.
        delay = backoff_seconds * (2 ** max(0, consecutive_failures - 1))
        _report(
            progress,
            f"connection lost: {reconnect_reason}; reconnecting in {_format_seconds(delay)}",
        )
        sleeper(delay)


def _finalize(
    parts: list[Path],
    output_path: Path | None,
    finalizer: Callable[[Iterable[Path], Path], Path],
    records: tuple[ConnectionRecord, ...],
    parts_directory: Path,
    progress: Callable[[str], None] | None,
    *,
    interrupted: bool = False,
) -> CaptureResult:
    if output_path is None:
        return CaptureResult(tuple(parts), None, interrupted, records)
    try:
        _report(progress, "finalizing")
        if finalizer is finalize_parts:
            output = finalizer(parts, output_path, progress=progress)
        else:
            output = finalizer(parts, output_path)
    except KeyboardInterrupt:
        return CaptureResult(tuple(parts), None, True, records)
    except Exception as error:
        raise CaptureError(f"finalization failed: {error}", tuple(parts)) from error
    _report(progress, f"output written: {output} ({output.stat().st_size} bytes)")
    return CaptureResult(tuple(parts), output, interrupted, records)


def _report(progress: Callable[[str], None] | None, message: str) -> None:
    if progress is not None:
        progress(message)


def _safe_reason(error: Exception) -> str:
    return _URL_PATTERN.sub("[URL redacted]", str(error))


def _format_seconds(seconds: float) -> str:
    return f"{seconds:g}s"


def _append_connection_record(path: Path, record: ConnectionRecord) -> None:
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
            }
            for timing in record.part_timings
        ],
        "outcome": record.outcome,
        "error": record.error,
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(values, sort_keys=True) + "\n")
        handle.flush()
        # A process killed between reconnects must not lose the closed record.
        os.fsync(handle.fileno())


def _validate_limits(failures: int, empty: int, backoff: float) -> None:
    if not isinstance(failures, int) or failures < 1:
        raise ValueError("max_consecutive_failures must be a positive integer")
    if not isinstance(empty, int) or empty < 1:
        raise ValueError("max_consecutive_empty_connections must be a positive integer")
    if backoff < 0:
        raise ValueError("backoff_seconds must not be negative")
