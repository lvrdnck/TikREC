"""Coordinate tag acquisition, part writing, and optional finalization."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

from .finalize import finalize_parts
from .flv import FlvTag
from .source import iter_url_tags
from .writer import write_parts


class CaptureError(RuntimeError):
    """Raised when capture or finalization fails after preserving part files."""

    def __init__(self, message: str, parts: tuple[Path, ...] = ()) -> None:
        super().__init__(message)
        self.parts = parts


@dataclass(frozen=True)
class CaptureResult:
    """The completed parts, optional final output, and interruption state."""

    parts: tuple[Path, ...]
    output_path: Path | None
    interrupted: bool = False


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
    writer: Callable[[Iterable[FlvTag], Path], tuple[Path, ...]] = write_parts,
    finalizer: Callable[[Iterable[Path], Path], Path] = finalize_parts,
) -> CaptureResult:
    """Record one already-direct FLV URL using injectable acquisition helpers."""
    return capture_tags(
        tag_source(url),
        parts_directory=parts_directory,
        output_path=output_path,
        writer=writer,
        finalizer=finalizer,
    )


def _prepare_session(parts_directory: Path, output_path: Path | None) -> None:
    if parts_directory.exists():
        raise FileExistsError(f"refusing to reuse existing session directory: {parts_directory}")
    if output_path is not None and output_path.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {output_path}")
    parts_directory.mkdir(parents=True)


def _completed_parts(parts_directory: Path) -> tuple[Path, ...]:
    return tuple(sorted(parts_directory.glob("part-*.flv")))
