"""Best-effort inspection of completed recording outputs."""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class MediaInfo:
    """Optional stream facts reported by FFprobe for a completed output."""

    video_codec: str | None = None
    audio_codec: str | None = None
    width: int | None = None
    height: int | None = None


def inspect_media(
    path: Path,
    *,
    ffprobe: str = "ffprobe",
    runner: Callable[..., Any] = subprocess.run,
) -> MediaInfo | None:
    """Return optional codec and resolution facts without raising probe failures."""
    try:
        result = runner(
            [
                ffprobe, "-v", "error", "-show_streams", "-show_entries",
                "stream=codec_type,codec_name,width,height", "-of", "json", str(path),
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        document = json.loads(result.stdout) if result.returncode == 0 else None
    except (OSError, TypeError, AttributeError, json.JSONDecodeError, subprocess.SubprocessError):
        return None
    streams = document.get("streams") if isinstance(document, dict) else None
    if not isinstance(streams, list):
        return None
    video = _first_stream(streams, "video")
    audio = _first_stream(streams, "audio")
    return MediaInfo(
        _string_value(video, "codec_name"),
        _string_value(audio, "codec_name"),
        _positive_int(video, "width"),
        _positive_int(video, "height"),
    )


def _first_stream(streams: list[Any], codec_type: str) -> dict[str, Any]:
    return next(
        (
            stream
            for stream in streams
            if isinstance(stream, dict) and stream.get("codec_type") == codec_type
        ),
        {},
    )


def _string_value(values: dict[str, Any], key: str) -> str | None:
    value = values.get(key)
    return value if isinstance(value, str) and value else None


def _positive_int(values: dict[str, Any], key: str) -> int | None:
    value = values.get(key)
    return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else None
