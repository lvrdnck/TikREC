"""Media checks shared by output and session validation."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any, TYPE_CHECKING

from .media import MediaInfo, inspect_media
from .part_validation import validate_decoding

if TYPE_CHECKING:
    from .validation import _ResultBuilder


def _validate_output(
    output: Path, result: _ResultBuilder, deep: bool, ffprobe: str, runner: Callable[..., Any]
) -> MediaInfo | None:
    if not _readable_nonempty(output, result, "output"):
        result.media_integrity = "failed"
        result.final_output_inspection = "failed"
        return None
    info = inspect_media(output, ffprobe=ffprobe, runner=runner)
    if info is None:
        result.finding("error", "output_probe_failed", "FFprobe could not inspect the output", output)
        result.media_integrity = "failed"
        result.final_output_inspection = "failed"
        return None
    failed = False
    for code, value, message in (
        ("output_video_missing", info.video_codec, "no recognizable video stream"),
        ("output_format_missing", info.format_name, "container format was not recognized"),
        ("output_duration_invalid", info.duration_seconds, "duration is missing or not positive"),
    ):
        if value is None:
            result.finding("error", code, message, output)
            failed = True
    if info.audio_codec is None:
        result.finding("warning", "output_audio_missing", "no recognizable audio stream", output)
    result.final_output_inspection = "failed" if failed else "passed"
    if deep:
        try:
            decode_error = validate_decoding(output, ffprobe, runner)
        except OSError as error:
            decode_error = f"could not start FFprobe: {error}"
        if decode_error is not None:
            result.finding("error", "output_decode", decode_error, output)
            failed = True
        result.final_output_decode = "failed" if decode_error is not None else "passed"
    if result.media_integrity != "failed":
        result.media_integrity = "failed" if failed else "passed"
    return info

def _readable_nonempty(path: Path, result: _ResultBuilder, prefix: str) -> bool:
    try:
        if not path.is_file() or path.stat().st_size == 0:
            reason = "is not a non-empty regular file"
            raise ValueError(reason)
        with path.open("rb") as handle:
            handle.read(1)
    except (OSError, ValueError) as error:
        result.finding("error", f"{prefix}_unreadable", str(error), path)
        return False
    return True

def _compare_media(
    declared: Any, actual: MediaInfo, result: _ResultBuilder, output: Path
) -> None:
    if declared is None:
        return
    if not isinstance(declared, dict):
        result.finding("error", "manifest_media_invalid", "manifest media is not an object")
        return
    for key in ("video_codec", "audio_codec", "width", "height"):
        expected = declared.get(key)
        if expected is not None and expected != getattr(actual, key):
            result.finding(
                "error", "manifest_media_mismatch",
                f"manifest {key} is {expected!r}, FFprobe reports {getattr(actual, key)!r}",
                output,
            )
