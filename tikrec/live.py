"""Reconnect public TikTok LIVE capture without changing direct-FLV capture."""

from __future__ import annotations

import time
from collections.abc import Callable, Iterable
from pathlib import Path
from threading import Event

from .capture_control import CaptureControl, CaptureStopped
from .capture import (
    CaptureError, CaptureResult, ConnectionRecord, _prepare_session,
    append_connection_record, append_room_status_record,
)
from .finalize import finalize_parts
from .connection_observation import ConnectionObservation
from .flv import FlvTag
from .manifest import SessionManifest
from .media import MediaInfo, inspect_media
from .source import RawCopy, SourceStallError, iter_url_tags
from .tiktok import (TikTokOfflineError, TikTokResolutionError,
                     TikTokResolutionTransientError, resolve_live_url,
                     resolve_live_url_confirmed)
from .tiktok_bound import resolve_live_url_bound
from .writer import PartTiming, TimestampReplay, write_parts
from .live_source import connection_source
from .live_session import finish_live, fail_live, close_live_connection
from .live_recovery import (LiveRecovery, OutageCaptureError, SourceNetworkError,
                            SourceRefreshError, resolve_bound_live)
from .retry_policy import RetryPolicy, RecoveryExhausted
from .live_support import (_report, _warn, _safe_reason, _timestamp_replay_message,
                           _next_failure_counts, _validate_limits, LiveChangedError)


def capture_live(
    url: str,
    *,
    parts_directory: Path,
    output_path: Path | None = None,
    resolver: Callable[[str], str] = resolve_live_url, bound_resolver=None,
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
    stop_event: Event | None = None,
    state: Callable[[str], None] | None = None,
    session_id: str | None = None,
    room_identity: Callable[[str], None] | None = None,
    _resume_session=None,
    retry_policy: RetryPolicy | None = RetryPolicy(),
    recovery_clock: Callable[[], float] = time.monotonic,
    recovery_observer: Callable[[dict], None] | None = None,
    recovery_waiter=None,
) -> CaptureResult:
    """Record a public LIVE page through reconnects until confirmed offline."""
    _validate_limits(max_consecutive_failures, max_consecutive_empty_connections, backoff_seconds,
                     offline_confirmation_checks, offline_confirmation_interval)
    parts_directory = Path(parts_directory)
    output_path = Path(output_path) if output_path is not None else None
    manifest = SessionManifest(parts_directory, output_path, "tiktok_live",
                               clock=manifest_clock, media_inspector=media_inspector,
                               session_id=session_id)
    control = CaptureControl(stop_event, sleeper, waiter=recovery_waiter)
    if bound_resolver is None and resolver is resolve_live_url:
        bound_resolver = resolve_live_url_bound

    records: list[ConnectionRecord] = []
    all_parts: list[Path] = []
    next_part_index = 1
    consecutive_failures = 0
    consecutive_empty = 0
    connection_number = 0
    previous_end: float | None = None
    session_started = False
    delay = 0.0
    if _resume_session is not None:
        # Explicit preflight owns old media; each loop iteration still creates a fresh writer.
        manifest = _resume_session.manifest
        all_parts = list(_resume_session.retained.parts)
        next_part_index = _resume_session.retained.next_index
        connection_number = _resume_session.next_connection - 1
        previous_end = _resume_session.previous_end
        session_started = True

    saved_room_id = manifest.snapshot().get("room_id") if manifest.active else None
    recovery = LiveRecovery(retry_policy or RetryPolicy(), clock=recovery_clock, wall_clock=manifest_clock,
                            directory=parts_directory, manifest=manifest, observer=recovery_observer)

    def finish(interrupted: bool = False) -> CaptureResult:
        return finish_live(all_parts, output_path, manifest=manifest, records=records,
                           finalizer=finalizer, state=state, progress=progress, interrupted=interrupted,
                           connection_count=connection_number)

    def capture_failure(message: str) -> CaptureError:
        return fail_live(message, all_parts, manifest=manifest, output_path=output_path, connection_count=connection_number)

    while True:
        try:
            control.check()
            if connection_number:
                # Wait before measuring the attempt so reconnect gap evidence includes backoff.
                if recovery.outage.active:
                    recovery.notify("wait")
                    recovery.outage.wait(control)
                else:
                    control.wait(delay)
        except RecoveryExhausted as error:
            recovery.end("exhausted")
            failure = capture_failure(str(error))
            raise OutageCaptureError(str(failure), failure.parts) from error
        except (KeyboardInterrupt, CaptureStopped):
            recovery.end("user_stop")
            return finish(interrupted=True)
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
            ended_at = close_live_connection(
                directory=parts_directory, number=connection_number, started_at=started_at,
                outcome=outcome, error=error,
                previous_end=previous_end, parts=connection_parts, timings=part_timings,
                raw_copy=raw_copy, observation=observation, session_started=session_started,
                records=records, all_parts=all_parts, manifest=manifest, clock=clock,
                # Repeated resolver-only failures are coalesced by the outage boundaries.
                persist_record=not (outcome == "resolver_error" and recovery.outage.active))
            # This advances from writer output, rather than inspecting the directory.
            next_part_index += len(connection_parts)
            previous_end = ended_at

        try:
            control.check()
            _report(state, "resolving")
            _report(progress, "resolving room")
            direct_url = resolve_live_url_confirmed(
                url,
                resolver=lambda page: control.resolve(
                    lambda target: resolve_bound_live(resolver, target, saved_room_id,
                        bound_resolver=bound_resolver, wall_clock=manifest_clock), page),
                capture_started=bool(all_parts),
                checks=offline_confirmation_checks,
                interval=offline_confirmation_interval,
                sleeper=control.wait,
                clock=clock,
                # A pre-capture status must not create the session it failed to start.
                status_observer=lambda timestamp, status, confirmed: append_room_status_record(
                    parts_directory / "connections.jsonl", timestamp, status, confirmed
                ) if session_started else None,
            )
            observation.resolved(direct_url)
            control.check()
            resolved_room = getattr(direct_url, "room_id", None)
            saved_room_id = saved_room_id or resolved_room
            if resolved_room is not None and room_identity is not None:
                # Durable identity is committed before opening the first media connection.
                room_identity(resolved_room)
            if not session_started:
                _prepare_session(parts_directory, output_path)
                session_started = True
                manifest.start(connection_count=connection_number)
                # Preserve transient attempts once resolution creates a real session.
                for pending_record in records:
                    append_connection_record(parts_directory / "connections.jsonl", pending_record)
            if resolved_room is not None:
                manifest.record_room_identity(resolved_room)
            _report(progress, f"connection {connection_number} opened")
            _report(state, "recording")
            tags, raw_copy = connection_source(
                direct_url, number=connection_number, raw_copy_dir=raw_copy_dir,
                raw_tag_source=raw_tag_source, tag_source=tag_source,
                observation=observation, control=control,
                warning=lambda message: _warn(warning, progress, message),
            )
            controlled_tags = control.tags(observation.tags(tags))
            try:
                written_parts = writer(
                    controlled_tags,
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
                # Explicit closure also covers injected writers that return early.
                controlled_tags.close()
                close = getattr(tags, "close", None)
                if close is not None:
                    close()
                if raw_copy is not None:
                    raw_copy.close()
            # Custom writers may not use the callback, while the built-in writer does.
            if not connection_parts:
                connection_parts.extend(written_parts)
        except FileExistsError:
            raise
        except (KeyboardInterrupt, CaptureStopped):
            close_record("interrupted")
            recovery.end("user_stop")
            return finish(interrupted=True)
        except LiveChangedError as error:
            # A proven different room is an end without a fabricated non-live status response.
            close_record("live_changed", error)
            recovery.end("live_changed")
            return finish()
        except TikTokOfflineError as error:
            close_record("offline", error)
            recovery.end("offline")
            _report(progress, "room ended")
            if not all_parts:
                raise capture_failure("TikTok account or room is not live") from error
            return finish()
        except TikTokResolutionTransientError as error:
            close_record("resolver_error", error)
            consecutive_failures, consecutive_empty = _next_failure_counts(bool(connection_parts), consecutive_failures, consecutive_empty)
            reconnect_reason = _safe_reason(error)
            error_for_retry = error
        except (SourceNetworkError, SourceRefreshError) as error:
            close_record("stalled" if isinstance(error.original, SourceStallError) else "connection_error", error)
            if isinstance(error, SourceRefreshError) and (not all_parts or saved_room_id is None):
                recovery.end("failed")
                raise capture_failure("media source was unavailable before capture identity was established") from error
            consecutive_failures, consecutive_empty = _next_failure_counts(bool(connection_parts), consecutive_failures, consecutive_empty)
            reconnect_reason = _safe_reason(error)
            error_for_retry = None if isinstance(error, SourceRefreshError) else error
        except TikTokResolutionError as error:
            close_record("resolution_error", error)
            recovery.end("failed")
            raise capture_failure(
                f"TikTok LIVE resolution failed: {_safe_reason(error)}"
            ) from error
        except Exception as error:
            close_record("capture_error", error)
            recovery.end("failed")
            raise capture_failure(f"live capture failed: {_safe_reason(error)}") from error
        else:
            close_record("closed")
            if connection_parts:
                recovery.end("recovered")
            consecutive_failures = 0
            consecutive_empty = 0 if connection_parts else consecutive_empty + 1
            reconnect_reason = "connection closed"
            if consecutive_empty >= max_consecutive_empty_connections:
                raise capture_failure(
                    "live capture stopped after consecutive connections with no media"
                )

        if (retry_policy is not None and saved_room_id is not None
                and reconnect_reason != "connection closed" and error_for_retry is not None):
            if connection_parts:
                recovery.end("recovered")
            # A source error after useful media starts a new outage, rather than exhausting the old one.
            recovery.failure(error_for_retry)
        elif consecutive_failures >= max_consecutive_failures:
            raise capture_failure(
                "live capture stopped after consecutive connection failures"
            )
        # Healthy media EOF can resolve immediately; every failure keeps its existing wait.
        delay = (0.0 if reconnect_reason == "connection closed" and connection_parts else
                 recovery.outage.status()["next_retry_in_seconds"] if recovery.outage.active
                 else backoff_seconds * (2 ** max(0, consecutive_failures - 1)))
        _report(progress, f"connection lost: {reconnect_reason}; reconnecting in {delay:g}s")
        _report(state, "recovering_network" if recovery.outage.active else "reconnecting")
