"""Finalize completed FLV parts into one media file with FFmpeg."""

from __future__ import annotations

import os
import shlex
import subprocess
from collections.abc import Callable, Iterable
from fractions import Fraction
from pathlib import Path
from typing import Any

from .flv import FlvFormatError, avc_configuration_dimensions
from .decode_diagnostics import DecodeDiagnostics, input_decode_health
from .ffmpeg_progress import FfmpegProgressReporter
from .frame_rate import inspect_frame_rate, nominal_frame_rate
# Re-export the existing internal helpers to preserve injected callers/tests.
from .finalize_media import (
    _validate_parts, _validate_output_path, _temporary_output_path,
    _configuration_for, _file_chunks, _write_concat_manifest, _concat_path,
    _build_ffmpeg_command, _concat_filter,
)


class FinalizationError(RuntimeError):
    """Raised when FFmpeg cannot produce a complete final media file."""


def finalize_parts(
    parts: Iterable[Path],
    output_path: Path,
    *,
    ffmpeg: str | Path = "ffmpeg",
    runner: Callable[..., Any] = subprocess.run,
    progress: Callable[[str], None] | None = None,
    frame_rate_inspector: Callable[[Path], Fraction] = inspect_frame_rate,
    on_input_decode: Callable[[dict], None] | None = None,
) -> Path:
    """Stitch parts, reporting fixed input-decoder evidence when requested."""
    ordered_parts = _validate_parts(parts)
    output_path = Path(output_path)
    _validate_output_path(output_path)
    configurations = tuple(_configuration_for(part) for part in ordered_parts)
    same_configuration = len(set(configurations)) == 1
    diagnostics = None if same_configuration else DecodeDiagnostics()
    target_size = _target_size(configurations) if not same_configuration else None
    nominal_rate = (
        nominal_frame_rate(ordered_parts, inspector=frame_rate_inspector)
        if not same_configuration else None
    )
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
            nominal_rate=nominal_rate,
        )
        if progress is not None:
            if same_configuration:
                progress(
                    f"finalization started: stream-copying {len(ordered_parts)} part(s)"
                )
            else:
                progress(
                    f"finalization started: re-encoding {len(ordered_parts)} part(s); "
                    "this may take several minutes or longer"
                )
        result = _run_ffmpeg(command, runner, progress, diagnostics)
        if result.returncode != 0:
            raise FinalizationError(_ffmpeg_failure(command, result.stderr, result.returncode))
        if not temporary_output.is_file():
            raise FinalizationError("FFmpeg exited successfully but did not create output")
        if on_input_decode is not None:
            on_input_decode(input_decode_health("not_checked") if diagnostics is None
                            else diagnostics.result())

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


def _run_ffmpeg(
    command: list[str],
    runner: Callable[..., Any],
    progress: Callable[[str], None] | None,
    diagnostics: DecodeDiagnostics | None = None,
) -> Any:
    if runner is not subprocess.run:
        try:
            result = runner(command, capture_output=True, text=True, check=False)
        except OSError as error:
            raise FinalizationError(f"could not start FFmpeg: {error}") from error
        if diagnostics is not None:
            for line in (result.stderr or "").splitlines():
                diagnostics.observe(line)
        FfmpegProgressReporter(progress).report(result.stderr)
        return result

    # FFmpeg writes both structured progress and diagnostics to stderr. Retain
    # every line so a non-zero exit still reports the actual diagnostic.
    progress_command = command[:2] + [
        "-progress", "pipe:2", "-nostats", "-loglevel", "warning",
    ] + command[2:] if progress is not None else command
    try:
        process = subprocess.Popen(
            progress_command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
    except OSError as error:
        raise FinalizationError(f"could not start FFmpeg: {error}") from error

    assert process.stderr is not None
    stderr_lines: list[str] = []
    retained_chars = 0
    reporter = FfmpegProgressReporter(progress)
    try:
        for line in process.stderr:
            if diagnostics is not None:
                diagnostics.observe(line)
            # Keep failure diagnostics bounded even for hours of repeated warnings.
            if retained_chars < 16384:
                excerpt = line[:16384 - retained_chars]
                stderr_lines.append(excerpt)
                retained_chars += len(excerpt)
            reporter.report(line)
    except BaseException:
        # KeyboardInterrupt is not an Exception, but FFmpeg must not outlive
        # an abandoned finalization and keep its temporary output locked.
        process.terminate()
        process.wait()
        raise
    return subprocess.CompletedProcess(command, process.wait(), stderr="".join(stderr_lines))


def _target_size(configurations: tuple[bytes, ...]) -> tuple[int, int]:
    try:
        dimensions = [avc_configuration_dimensions(configuration) for configuration in configurations]
    except FlvFormatError as error:
        raise ValueError(f"could not determine AVC dimensions: {error}") from error
    return max(width for width, _ in dimensions), max(height for _, height in dimensions)


def _ffmpeg_failure(command: list[str], stderr: str | None, returncode: int) -> str:
    detail = stderr.strip() if stderr and stderr.strip() else "FFmpeg produced no stderr"
    return f"FFmpeg exited with code {returncode}: {detail}\ncommand: {shlex.join(command)}"
