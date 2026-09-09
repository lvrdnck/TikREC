"""Finalize completed FLV parts into one media file with FFmpeg."""

from __future__ import annotations

import os
import shlex
import subprocess
from collections.abc import Callable, Iterable, Iterator
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from .flv import FlvFormatError, avc_configuration_dimensions
from .source import iter_tags


class FinalizationError(RuntimeError):
    """Raised when FFmpeg cannot produce a complete final media file."""


def finalize_parts(
    parts: Iterable[Path],
    output_path: Path,
    *,
    ffmpeg: str | Path = "ffmpeg",
    runner: Callable[..., Any] = subprocess.run,
) -> Path:
    """Stitch completed FLV parts into ``output_path`` and return that path."""
    ordered_parts = _validate_parts(parts)
    output_path = Path(output_path)
    _validate_output_path(output_path)
    configurations = tuple(_configuration_for(part) for part in ordered_parts)
    same_configuration = len(set(configurations)) == 1
    target_size = _target_size(configurations) if not same_configuration else None
    temporary_output = _temporary_output_path(output_path)
    if temporary_output.exists():
        raise FileExistsError(f"temporary output already exists: {temporary_output}")

    manifest: Path | None = None
    try:
        if same_configuration:
            manifest = _write_concat_manifest(ordered_parts, output_path.parent)
        command = _build_ffmpeg_command(
            ordered_parts,
            temporary_output,
            ffmpeg=ffmpeg,
            manifest=manifest,
            target_size=target_size,
        )
        try:
            result = runner(command, capture_output=True, text=True, check=False)
        except OSError as error:
            raise FinalizationError(f"could not start FFmpeg: {error}") from error
        if result.returncode != 0:
            raise FinalizationError(_ffmpeg_failure(command, result.stderr, result.returncode))
        if not temporary_output.is_file():
            raise FinalizationError("FFmpeg exited successfully but did not create output")

        # The destination has been checked absent, so promotion cannot replace
        # a finished recording while finalization is in progress.
        os.replace(temporary_output, output_path)
        if not output_path.is_file():
            raise FinalizationError("FFmpeg output could not be promoted")
        return output_path
    finally:
        if manifest is not None:
            manifest.unlink(missing_ok=True)
        # Remove any output from a failed FFmpeg run instead of leaving a file
        # whose partial filename might be mistaken for a recoverable recording.
        temporary_output.unlink(missing_ok=True)


def _validate_parts(parts: Iterable[Path]) -> tuple[Path, ...]:
    # Writer names parts with zero-padded indexes; the full path breaks ties
    # deterministically if callers supply identically named files from directories.
    ordered_parts = tuple(
        sorted((Path(part) for part in parts), key=lambda part: (part.name, str(part)))
    )
    if not ordered_parts:
        raise ValueError("at least one completed FLV part is required")
    for part in ordered_parts:
        if not part.is_file():
            raise FileNotFoundError(f"completed FLV part is missing: {part}")
    return ordered_parts


def _validate_output_path(output_path: Path) -> None:
    if not output_path.parent.is_dir():
        raise ValueError(f"output directory does not exist: {output_path.parent}")
    if output_path.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {output_path}")
    if not output_path.suffix:
        raise ValueError("output path must have a container extension")


def _temporary_output_path(output_path: Path) -> Path:
    """Return a hidden temporary path that retains FFmpeg's output suffix."""
    suffix = output_path.suffix
    stem = output_path.name[: -len(suffix)]
    # FFmpeg chooses its muxer from the last suffix, so ``.partial`` belongs
    # before it rather than after it. Keeping the directory unchanged permits
    # ``os.replace`` to remain atomic on filesystems that support it.
    return output_path.with_name(f".{stem}.partial{suffix}")


def _configuration_for(part: Path) -> bytes:
    try:
        for tag in iter_tags(_file_chunks(part)):
            if tag.is_avc_configuration:
                return tag.payload[5:]
    except (EOFError, FlvFormatError) as error:
        raise ValueError(f"invalid completed FLV part {part}: {error}") from error
    raise ValueError(f"completed FLV part has no AVC configuration: {part}")


def _file_chunks(path: Path, chunk_size: int = 64 * 1024) -> Iterator[bytes]:
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            yield chunk


def _target_size(configurations: tuple[bytes, ...]) -> tuple[int, int]:
    try:
        dimensions = [avc_configuration_dimensions(configuration) for configuration in configurations]
    except FlvFormatError as error:
        raise ValueError(f"could not determine AVC dimensions: {error}") from error
    return max(width for width, _ in dimensions), max(height for _, height in dimensions)


def _write_concat_manifest(parts: tuple[Path, ...], directory: Path) -> Path:
    with NamedTemporaryFile(
        mode="w", encoding="utf-8", suffix=".ffconcat", prefix=".tikrec-", dir=directory,
        delete=False,
    ) as handle:
        for part in parts:
            handle.write(f"file {_concat_path(part.resolve())}\n")
        return Path(handle.name)


def _concat_path(path: Path) -> str:
    # The concat demuxer uses single quotes; escape them without invoking a shell.
    return "'" + str(path).replace("'", r"'\''") + "'"


def _build_ffmpeg_command(
    parts: tuple[Path, ...],
    temporary_output: Path,
    *,
    ffmpeg: str | Path,
    manifest: Path | None,
    target_size: tuple[int, int] | None,
) -> list[str]:
    command = [str(ffmpeg), "-nostdin", "-n"]
    if manifest is not None:
        return command + [
            "-f", "concat", "-safe", "0", "-i", str(manifest),
            "-map", "0", "-c", "copy", "-movflags", "+faststart", str(temporary_output),
        ]

    assert target_size is not None
    for part in parts:
        command.extend(["-i", str(part)])
    command.extend([
        "-filter_complex", _concat_filter(len(parts), target_size),
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-c:a", "aac", "-movflags", "+faststart",
        str(temporary_output),
    ])
    return command


def _concat_filter(part_count: int, target_size: tuple[int, int]) -> str:
    width, height = target_size
    filters = []
    for index in range(part_count):
        # Reset every part independently before concat; otherwise rebased FLV
        # timestamps can leave a gap or push audio away from its video segment.
        filters.append(
            f"[{index}:v:0]scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1,setpts=PTS-STARTPTS[v{index}]"
        )
        filters.append(f"[{index}:a:0]asetpts=PTS-STARTPTS[a{index}]")
    inputs = "".join(f"[v{index}][a{index}]" for index in range(part_count))
    filters.append(f"{inputs}concat=n={part_count}:v=1:a=1[v][a]")
    return ";".join(filters)


def _ffmpeg_failure(command: list[str], stderr: str | None, returncode: int) -> str:
    detail = stderr.strip() if stderr and stderr.strip() else "FFmpeg produced no stderr"
    return f"FFmpeg exited with code {returncode}: {detail}\ncommand: {shlex.join(command)}"
