"""Coordinate tag acquisition, part writing, and optional finalization."""

from __future__ import annotations

import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

from .finalize import finalize_parts
from .connection_observation import ConnectionObservation
from .flv import FlvTag
from .manifest import SessionManifest, _safe_reason
from .media import MediaInfo, inspect_media
from .source import RawCopy, iter_url_tags
from .writer import PartTiming, write_parts
from .connection_log import ConnectionRecord, append_connection_record, append_room_status_record
from .capture_control import CaptureStopped
from .session_parts import part_order


class CaptureError(RuntimeError):
    """Raised when capture or finalization fails after preserving part files."""

    def __init__(self, message: str, parts: tuple[Path, ...] = ()) -> None:
        super().__init__(message)
        self.parts = parts


@dataclass(frozen=True)
class CaptureResult:
    """The completed parts, final output, interruption state, and connections."""

    parts: tuple[Path, ...]
    output_path: Path | None
    interrupted: bool = False
    connections: tuple[ConnectionRecord, ...] = ()
    resumed: bool = False
    resume_start_index: int | None = None


def capture_tags(
    tags: Iterable[FlvTag],
    *,
    parts_directory: Path,
    output_path: Path | None = None,
    writer: Callable[[Iterable[FlvTag], Path], tuple[Path, ...]] = write_parts,
    finalizer: Callable[[Iterable[Path], Path], Path] = finalize_parts,
    source_type: str = "tag_stream",
    connection_count: int = 0,
    clock: Callable[[], float] = time.time,
    media_inspector: Callable[[Path], MediaInfo | None] = inspect_media,
) -> CaptureResult:
    """Record supplied tags, optionally finalize them, and return their paths."""
    parts_directory = Path(parts_directory)
    output_path = Path(output_path) if output_path is not None else None
    _prepare_session(parts_directory, output_path)
    manifest = SessionManifest(parts_directory, output_path, source_type,
                               clock=clock, media_inspector=media_inspector)
    manifest.start(connection_count=connection_count)
    return _capture_session(tags, parts_directory, output_path, manifest, writer, finalizer)


def _capture_session(tags, parts_directory, output_path, manifest, writer, finalizer,
                     *, retained_parts=(), progress=None):
    """Share writer unwind and finalization semantics between capture entry points."""
    interrupted = False
    try:
        parts = tuple(retained_parts) + tuple(writer(tags, parts_directory))
    except (KeyboardInterrupt, CaptureStopped):
        interrupted = True
        parts = _completed_parts(parts_directory)
        if retained_parts:
            parts = tuple(sorted(parts, key=part_order))
    except Exception as error:
        parts = _completed_parts(parts_directory)
        if retained_parts:
            parts = tuple(sorted(parts, key=part_order))
        # Explicit resume diagnostics must not disclose the supplied ephemeral transport URL.
        reason = _safe_reason(error) if retained_parts else str(error)
        failure = CaptureError(f"capture failed: {reason}", parts)
        finalization = "not_started" if output_path is not None else None
        manifest.fail(parts, failure, finalization_status=finalization)
        raise failure from error

    if not parts:
        if interrupted:
            finalization = "not_started" if output_path is not None else None
            manifest.complete(parts, interrupted=True, finalization_status=finalization)
            return CaptureResult(parts, None, True)
        if output_path is None:
            manifest.complete(parts)
            return CaptureResult(parts, None, interrupted)
        failure = CaptureError("capture produced no completed FLV parts")
        manifest.fail(parts, failure, finalization_status="not_started")
        raise failure
    return finalize_capture_result(parts, output_path, finalizer=finalizer,
                                   interrupted=interrupted, manifest=manifest, progress=progress)


def finalize_capture_result(
    parts: Iterable[Path],
    output_path: Path | None,
    *,
    finalizer: Callable[[Iterable[Path], Path], Path] = finalize_parts,
    interrupted: bool = False,
    connections: tuple[ConnectionRecord, ...] = (),
    progress: Callable[[str], None] | None = None,
    manifest: SessionManifest | None = None,
) -> CaptureResult:
    """Optionally finalize retained parts and preserve capture result state."""
    completed_parts = tuple(parts)
    if output_path is None:
        if manifest is not None:
            manifest.complete(completed_parts, interrupted=interrupted)
        return CaptureResult(completed_parts, None, interrupted, connections)
    try:
        if manifest is not None:
            manifest.mark_finalizing(completed_parts)
        if progress is not None:
            end = "capture stopped by interrupt" if interrupted else "capture ended"
            progress(f"{end}; finalizing {len(completed_parts)} retained part(s)")
        if finalizer is finalize_parts:
            final_output = finalizer(completed_parts, output_path, progress=progress)
        else:
            final_output = finalizer(completed_parts, output_path)
    except KeyboardInterrupt:
        if manifest is not None:
            manifest.complete(
                completed_parts,
                interrupted=True,
                finalization_status="interrupted",
                error="finalization interrupted",
            )
        return CaptureResult(completed_parts, None, True, connections)
    except Exception as error:
        failure = CaptureError(f"finalization failed: {error}", completed_parts)
        if manifest is not None:
            manifest.fail(completed_parts, failure, finalization_status="failed")
        raise failure from error
    if progress is not None:
        progress(f"output written: {final_output} ({final_output.stat().st_size} bytes)")
    if manifest is not None:
        manifest.complete(completed_parts, output_path=final_output,
                          interrupted=interrupted, finalization_status="completed")
    return CaptureResult(completed_parts, final_output, interrupted, connections)


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
    observation_clock: Callable[[], float] = time.time,
) -> CaptureResult:
    """Record one direct FLV URL, optionally retaining its raw HTTP bytes."""
    raw_copy: RawCopy | None = None
    parts: tuple[Path, ...] = ()
    outcome = "closed"
    connection_error: Exception | None = None
    started_at = time.time()
    observation = ConnectionObservation(observation_clock)
    part_timings: list[PartTiming] = []

    def source() -> Iterable[FlvTag]:
        nonlocal raw_copy
        if raw_copy_dir is None:
            yield from (iter_url_tags(url, on_open=observation.opened)
                        if tag_source is iter_url_tags else tag_source(url))
            return
        if raw_tag_source is not None:
            raw_copy = RawCopy(raw_copy_path(raw_copy_dir, 1), warning,
                               connection_number=1, wall_clock=observation_clock)
            yield from raw_tag_source(url, raw_copy)
            return
        if tag_source is iter_url_tags:
            raw_copy = RawCopy(raw_copy_path(raw_copy_dir, 1), warning,
                               connection_number=1, wall_clock=observation_clock)
            yield from iter_url_tags(url, raw_copy=raw_copy, on_open=observation.opened)
            return
        if warning is not None:
            warning("raw copy is unavailable for a custom tag source")
        yield from tag_source(url)

    def observed_writer(tags: Iterable[FlvTag], directory: Path) -> tuple[Path, ...]:
        if writer is write_parts:
            return write_parts(tags, directory, on_media_retained=observation.retained,
                               on_part_closed=part_timings.append)
        return writer(tags, directory)

    try:
        result = capture_tags(
            observation.tags(source()),
            parts_directory=parts_directory,
            output_path=output_path,
            writer=observed_writer,
            finalizer=finalizer,
            source_type="direct_flv",
            connection_count=1,
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
                    part_timings=tuple(part_timings),
                    raw_copy=raw_copy.saved_path,
                    raw_arrivals=raw_copy.saved_arrivals_path,
                    **observation.values(),
                ),
            )


def raw_copy_path(directory: Path, connection_number: int) -> Path:
    return Path(directory) / f"connection-{connection_number:04d}.raw"


def _prepare_session(parts_directory: Path, output_path: Path | None) -> None:
    if parts_directory.exists():
        raise FileExistsError(f"refusing to reuse existing session directory: {parts_directory}")
    if output_path is not None and output_path.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {output_path}")
    parts_directory.mkdir(parents=True)


def _completed_parts(parts_directory: Path) -> tuple[Path, ...]:
    return tuple(sorted(parts_directory.glob("part-*.flv")))
