"""Retain connection evidence and finish the existing LIVE session lifecycle."""

from .capture import CaptureError, CaptureResult, finalize_capture_result
from .connection_log import ConnectionRecord, append_connection_record
from .live_support import _report, _safe_reason
from .capture_fence import close_connection_sources


def write_live_connection(writer, tags, raw, controlled, directory, fence, **options):
    """Unwind every source around the existing writer, including an early return."""
    try:
        return writer(controlled, directory, **options)
    finally:
        close_connection_sources(controlled, tags, raw, fence)


def finish_live(all_parts, output_path, *, manifest, records, finalizer, state,
                progress, interrupted=False, connection_count=None, capture_only=False):
    """Finish retained media using the shared finalizer and graceful-stop semantics."""
    if manifest.active and connection_count is not None:
        # Coalesced resolver failures advance the allocation count once when the episode closes.
        manifest.update_capture(all_parts, connection_count=connection_count)
    if capture_only:
        from .capture_completion import end_capture
        return end_capture(all_parts, output_path, manifest, records, interrupted)
    if all_parts:
        if output_path is not None:
            _report(state, "finalizing")
        return finalize_capture_result(
            all_parts, output_path, finalizer=finalizer, interrupted=interrupted,
            connections=tuple(records), progress=progress, manifest=manifest,
        )
    if manifest.active:
        finalization = "not_started" if output_path is not None else None
        manifest.complete(all_parts, interrupted=interrupted, finalization_status=finalization)
    return CaptureResult((), None, interrupted, tuple(records))



def fail_live(message, all_parts, *, manifest, output_path, connection_count=None, fence=None):
    """Close failed capture evidence while leaving every retained part on disk."""
    failure = CaptureError(message, tuple(all_parts))
    import sys
    original = sys.exc_info()[1]
    try:
        if manifest.active:
            if connection_count is not None:
                manifest.update_capture(all_parts, connection_count=connection_count)
            finalization = "not_started" if output_path is not None else None
            manifest.fail(all_parts, failure, finalization_status=finalization)
    except BaseException as cleanup:
        if fence is not None and original is not None:
            fence.primary_error = original
            fence.cleanup_errors.append(cleanup)
            raise original from cleanup
        raise
    return failure



def close_live_connection(*, directory, number, started_at, previous_end, parts, timings, outcome, error,
                          raw_copy, observation, session_started, records, all_parts, manifest, clock,
                          persist_record=True, fence=None):
    """Append a closed attempt and advance its manifest before the next connection."""
    ended_at = clock()
    record = ConnectionRecord(
        number,
        started_at,
        ended_at,
        None if previous_end is None else started_at - previous_end,
        tuple(parts),
        outcome,
        None if error is None else _safe_reason(error),
        tuple(timings),
        raw_copy=None if raw_copy is None else raw_copy.saved_path,
        raw_arrivals=None if raw_copy is None else raw_copy.saved_arrivals_path,
        **observation.values(),
    )
    try:
        if session_started and persist_record:
            append_connection_record(directory / "connections.jsonl", record)
        records.append(record)
        all_parts.extend(parts)
        if manifest.active and persist_record:
            manifest.update_capture(all_parts, connection_count=number)
    except BaseException as cleanup:
        if fence is not None and error is not None:
            fence.primary_error = error
            fence.cleanup_errors.append(cleanup)
            raise error from cleanup
        raise
    return ended_at
