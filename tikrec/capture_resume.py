"""Explicit generic capture continuation; callers own the source/resume decision."""

from __future__ import annotations

import time
from collections.abc import Callable, Iterable
from dataclasses import replace
from pathlib import Path
from threading import Event

from .capture import CaptureResult, _capture_session
from .capture_control import CaptureControl, CaptureStopped
from .connection_log import ConnectionRecord, append_connection_record, append_resume_record
from .connection_observation import ConnectionObservation
from .finalize import finalize_parts
from .flv import FlvTag
from .manifest import _safe_reason
from .media import MediaInfo, inspect_media
from .session_resume import prepare_resume
from .source import iter_url_tags
from .writer import write_parts


def capture_tags_resume(tags: Iterable[FlvTag], *, parts_directory: Path,
                        output_path: Path | None = None, **options) -> CaptureResult:
    """Continue a validated session with supplied tags and a fresh writer.

    Optional injections: writer, finalizer, clock, observation_clock, media_inspector,
    stop_event, session_id, source_type, progress, and heartbeat. No source identity
    or TikTok decision is inferred. None output means capture-only continuation.
    """
    return _resume_connection(lambda control, observation: tags,
                              parts_directory=parts_directory, output_path=output_path, **options)


def capture_url_resume(url: str, *, parts_directory: Path,
                       output_path: Path | None = None,
                       tag_source: Callable[[str], Iterable[FlvTag]] = iter_url_tags,
                       **options) -> CaptureResult:
    """Continue with one supplied direct FLV URL; never resolve or retry it.

    Accept the same optional injections as capture_tags_resume. Signed URLs remain
    internal transport and never enter the new resume/connection evidence.
    """
    def source(control, observation):
        if tag_source is iter_url_tags:
            return iter_url_tags(url, check_stop=control.check, on_open=observation.opened)
        return tag_source(url)

    return _resume_connection(source, parts_directory=parts_directory,
                              output_path=output_path, **options)


def _resume_connection(
    source, *, parts_directory: Path, output_path: Path | None,
    writer: Callable = write_parts, finalizer: Callable = finalize_parts,
    clock: Callable[[], float] = time.time,
    observation_clock: Callable[[], float] = time.time,
    media_inspector: Callable[[Path], MediaInfo | None] = inspect_media,
    stop_event: Event | None = None, session_id: str | None = None,
    source_type: str | None = None, progress: Callable[[str], None] | None = None,
    heartbeat: Callable[[Path, int], None] | None = None,
) -> CaptureResult:
    directory = Path(parts_directory)
    output = Path(output_path) if output_path is not None else None
    session = prepare_resume(directory, output_path=output, session_id=session_id,
                             source_type=source_type, clock=clock, media_inspector=media_inspector)
    started_at = clock()
    session.manifest.resume_capture(session.retained.parts, session.next_connection, output_path=output)
    # Persist the boundary before any source iterator can open a new network connection.
    append_resume_record(directory / "connections.jsonl", timestamp=started_at,
                         session_id=session.session_id, previous_status=session.previous_status,
                         connection=session.next_connection, next_part_index=session.retained.next_index)
    control = CaptureControl(stop_event, time.sleep)
    observation = ConnectionObservation(observation_clock)
    raw_tags = None
    new_parts, timings, records = [], [], []

    def connection_tags():
        nonlocal raw_tags
        raw_tags = source(control, observation)
        yield from observation.tags(raw_tags)

    controlled_tags = control.tags(connection_tags())

    def part_started(path):
        if progress is not None:
            progress(f"part started: {path.name}")

    def observed_writer(tags, target):
        outcome, error = "closed", None
        try:
            written = writer(tags, target, start_index=session.retained.next_index,
                             on_part_retained=new_parts.append, on_part_closed=timings.append,
                             on_part_started=part_started, on_progress=heartbeat,
                             **({"on_media_retained": observation.retained} if writer is write_parts else {}))
            # Injected writers may return parts without implementing the retain callback.
            if not new_parts:
                new_parts.extend(written)
            return tuple(new_parts)
        except BaseException as failure:
            outcome = "interrupted" if isinstance(failure, (KeyboardInterrupt, CaptureStopped)) else "connection_error"
            error = _safe_reason(failure)
            raise
        finally:
            controlled_tags.close()
            close = getattr(raw_tags, "close", None)
            if close is not None:
                close()
            ended_at = clock()
            record = ConnectionRecord(session.next_connection, started_at, ended_at,
                None if session.previous_end is None else started_at - session.previous_end,
                tuple(new_parts), outcome, error, tuple(timings), **observation.values())
            append_connection_record(directory / "connections.jsonl", record)
            records.append(record)
            session.manifest.update_capture(session.retained.parts + tuple(new_parts),
                                            connection_count=session.next_connection)

    result = _capture_session(controlled_tags, directory, output, session.manifest,
                              observed_writer, finalizer, retained_parts=session.retained.parts,
                              progress=progress)
    return replace(result, connections=tuple(records), resumed=True,
                   resume_start_index=session.retained.next_index)
