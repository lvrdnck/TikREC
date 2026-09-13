"""Reconnect public TikTok LIVE capture without changing direct-FLV capture."""

from __future__ import annotations

import time
from collections.abc import Callable, Iterable
from http.client import HTTPException
from pathlib import Path

from .capture import (
    CaptureError, CaptureResult, ConnectionRecord, _prepare_session,
    append_connection_record, append_room_status_record, finalize_capture_result,
    raw_copy_path,
)
from .finalize import finalize_parts
from .connection_observation import ConnectionObservation
from .flv import FlvTag
from .manifest import SessionManifest
from .media import MediaInfo, inspect_media
from .source import RawCopy, SourceStallError, iter_url_tags
from .tiktok import (
    TikTokOfflineError,
    TikTokResolutionError,
    TikTokResolutionTransientError,
    resolve_live_url,
    resolve_live_url_confirmed,
)
from .writer import PartTiming, TimestampReplay, write_parts


from .live_support import (_report, _warn, _safe_reason, _timestamp_replay_message,
                           _next_failure_counts, _validate_limits)


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
    offline_confirmation_checks: int = 3,
    offline_confirmation_interval: float = 5.0,
    sleeper: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.time,
    manifest_clock: Callable[[], float] = time.time,
    observation_clock: Callable[[], float] = time.time,
    progress: Callable[[str], None] | None = None,
    heartbeat: Callable[[Path, int], None] | None = None,
    raw_copy_dir: Path | None = None,
    raw_tag_source: Callable[[str, RawCopy], Iterable[FlvTag]] | None = None,
    warning: Callable[[str], None] | None = None,
    media_inspector: Callable[[Path], MediaInfo | None] = inspect_media,
) -> CaptureResult:
    """Record a public LIVE page through reconnects until confirmed offline."""
    _validate_limits(max_consecutive_failures, max_consecutive_empty_connections, backoff_seconds,
                     offline_confirmation_checks, offline_confirmation_interval)
    parts_directory = Path(parts_directory)
    output_path = Path(output_path) if output_path is not None else None
    manifest = SessionManifest(parts_directory, output_path, "tiktok_live",
                               clock=manifest_clock, media_inspector=media_inspector)

    records: list[ConnectionRecord] = []
    all_parts: list[Path] = []
    next_part_index = 1
    consecutive_failures = 0
    consecutive_empty = 0
    connection_number = 0
    previous_end: float | None = None
    session_started = False

    def capture_failure(message: str) -> CaptureError:
        failure = CaptureError(message, tuple(all_parts))
        if manifest.active:
            finalization = "not_started" if output_path is not None else None
            manifest.fail(all_parts, failure, finalization_status=finalization)
        return failure

    while True:
        connection_number += 1
        started_at = clock()
        connection_parts: list[Path] = []
        part_timings: list[PartTiming] = []
        raw_copy: RawCopy | None = None
        observation = ConnectionObservation(observation_clock)

        def retained(path: Path) -> None:
            # This callback preserves a part even when Ctrl-C interrupts writer.
            connection_parts.append(path)

        def part_closed(timing: PartTiming) -> None:
            part_timings.append(timing)

        def timestamp_replay(replay: TimestampReplay) -> None:
            _report(progress, _timestamp_replay_message(replay))

        def part_started(path: Path) -> None:
            _report(progress, f"part started: {path.name}")

        def close_record(outcome: str, error: Exception | None = None) -> None:
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
                None if raw_copy is None else raw_copy.saved_path,
                **observation.values(),
            )
            if session_started:
                append_connection_record(parts_directory / "connections.jsonl", record)
            records.append(record)
            all_parts.extend(connection_parts)
            if manifest.active:
                manifest.update_capture(all_parts, connection_count=len(records))
            # This advances from writer output, rather than inspecting the directory.
            next_part_index += len(connection_parts)
            previous_end = ended_at

        try:
            _report(progress, "resolving room")
            direct_url = resolve_live_url_confirmed(
                url,
                resolver=resolver,
                capture_started=bool(all_parts),
                checks=offline_confirmation_checks,
                interval=offline_confirmation_interval,
                sleeper=sleeper,
                clock=clock,
                # A pre-capture status must not create the session it failed to start.
                status_observer=lambda timestamp, status, confirmed: append_room_status_record(
                    parts_directory / "connections.jsonl", timestamp, status, confirmed
                ) if session_started else None,
            )
            observation.resolved(direct_url)
            if not session_started:
                _prepare_session(parts_directory, output_path)
                session_started = True
                manifest.start(connection_count=connection_number)
                # Preserve transient attempts once resolution creates a real session.
                for pending_record in records:
                    append_connection_record(parts_directory / "connections.jsonl", pending_record)
            _report(progress, f"connection {connection_number} opened")
            if raw_copy_dir is not None and raw_tag_source is not None:
                raw_copy = RawCopy(
                    raw_copy_path(raw_copy_dir, connection_number),
                    lambda message: _warn(warning, progress, message),
                )
                tags = raw_tag_source(direct_url, raw_copy)
            elif raw_copy_dir is not None and tag_source is iter_url_tags:
                raw_copy = RawCopy(
                    raw_copy_path(raw_copy_dir, connection_number),
                    lambda message: _warn(warning, progress, message),
                )
                tags = iter_url_tags(direct_url, raw_copy=raw_copy, on_open=observation.opened)
            else:
                if raw_copy_dir is not None:
                    _warn(warning, progress, "raw copy is unavailable for a custom tag source")
                tags = (iter_url_tags(direct_url, on_open=observation.opened)
                        if tag_source is iter_url_tags else tag_source(direct_url))
            try:
                written_parts = writer(
                    observation.tags(tags),
                    parts_directory,
                    start_index=next_part_index,
                    on_part_started=part_started,
                    on_progress=heartbeat,
                    on_part_retained=retained,
                    on_part_closed=part_closed,
                    on_timestamp_replay=timestamp_replay,
                    # Older injected writers need not implement the new observation hook.
                    **({"on_media_retained": observation.retained} if writer is write_parts else {}),
                )
            finally:
                if raw_copy is not None:
                    raw_copy.close()
            # Custom writers may not use the callback, while the built-in writer does.
            if not connection_parts:
                connection_parts.extend(written_parts)
        except FileExistsError:
            raise
        except KeyboardInterrupt:
            close_record("interrupted")
            if all_parts:
                return finalize_capture_result(
                    all_parts,
                    output_path,
                    finalizer=finalizer,
                    interrupted=True,
                    connections=tuple(records),
                    progress=progress,
                    manifest=manifest,
                )
            if manifest.active:
                finalization = "not_started" if output_path is not None else None
                manifest.complete(all_parts, interrupted=True, finalization_status=finalization)
            return CaptureResult(tuple(all_parts), None, True, tuple(records))
        except TikTokOfflineError as error:
            close_record("offline", error)
            _report(progress, "room ended")
            if not all_parts:
                raise capture_failure("TikTok account or room is not live") from error
            return finalize_capture_result(
                all_parts,
                output_path,
                finalizer=finalizer,
                connections=tuple(records),
                progress=progress,
                manifest=manifest,
            )
        except TikTokResolutionTransientError as error:
            close_record("resolver_error", error)
            consecutive_failures, consecutive_empty = _next_failure_counts(bool(connection_parts), consecutive_failures, consecutive_empty)
            reconnect_reason = _safe_reason(error)
        except SourceStallError as error:
            close_record("stalled", error)
            consecutive_failures, consecutive_empty = _next_failure_counts(bool(connection_parts), consecutive_failures, consecutive_empty)
            reconnect_reason = _safe_reason(error)
        # HTTP reads raise HTTPException (not OSError) when a CDN body ends early.
        except (OSError, EOFError, HTTPException) as error:
            close_record("connection_error", error)
            consecutive_failures, consecutive_empty = _next_failure_counts(bool(connection_parts), consecutive_failures, consecutive_empty)
            reconnect_reason = _safe_reason(error)
        except TikTokResolutionError as error:
            close_record("resolution_error", error)
            raise capture_failure(
                f"TikTok LIVE resolution failed: {_safe_reason(error)}"
            ) from error
        except Exception as error:
            close_record("capture_error", error)
            raise capture_failure(f"live capture failed: {_safe_reason(error)}") from error
        else:
            close_record("closed")
            consecutive_failures = 0
            consecutive_empty = 0 if connection_parts else consecutive_empty + 1
            reconnect_reason = "connection closed"
            if consecutive_empty >= max_consecutive_empty_connections:
                raise capture_failure(
                    "live capture stopped after consecutive connections with no media"
                )

        if consecutive_failures >= max_consecutive_failures:
            raise capture_failure(
                "live capture stopped after consecutive connection failures"
            )
        # Re-resolving after every close gets a fresh signed CDN URL.
        delay = backoff_seconds * (2 ** max(0, consecutive_failures - 1))
        _report(
            progress,
            f"connection lost: {reconnect_reason}; reconnecting in {delay:g}s",
        )
        sleeper(delay)
