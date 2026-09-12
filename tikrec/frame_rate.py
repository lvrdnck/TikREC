"""Derive an encoder-only nominal frame rate without resampling media."""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable, Iterable
from fractions import Fraction
from pathlib import Path
from typing import Any


def inspect_frame_rate(
    part: Path, *, ffprobe: str = "ffprobe", runner: Callable[..., Any] = subprocess.run,
) -> Fraction:
    """Return a positive rational video rate, preferring FFprobe's reported average."""
    try:
        result = runner(
            [ffprobe, "-v", "error", "-select_streams", "v:0", "-show_entries",
             "stream=avg_frame_rate,r_frame_rate", "-of", "json", str(part)],
            capture_output=True, text=True, check=False, timeout=30,
        )
        if result.returncode:
            raise ValueError(f"FFprobe exited {result.returncode}: {result.stderr}")
        document = json.loads(result.stdout)
        streams = document.get("streams", []) if isinstance(document, dict) else []
        stream = streams[0] if isinstance(streams, list) and streams else {}
        if isinstance(stream, dict):
            # r_frame_rate can be a timestamp-grid estimate, not the observed cadence.
            for key in ("avg_frame_rate", "r_frame_rate"):
                rate = _positive_rate(stream.get(key))
                if rate is not None:
                    return rate
        raise ValueError("no positive video frame rate")
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        raise ValueError(f"could not determine video frame rate for {part}: {error}") from error


def nominal_frame_rate(
    parts: Iterable[Path], *, inspector: Callable[[Path], Fraction] = inspect_frame_rate,
) -> Fraction:
    """Choose the highest part rate so slower segments cannot dilute the nominal rate."""
    rates = [inspector(part) for part in parts]
    if not rates or any(not isinstance(rate, Fraction) or rate <= 0 for rate in rates):
        raise ValueError("at least one positive rational frame rate per part is required")
    return max(rates)


def _positive_rate(value: Any) -> Fraction | None:
    if not isinstance(value, str):
        return None
    try:
        rate = Fraction(value)
    except (ValueError, ZeroDivisionError):
        return None
    # x264 stores both components in signed integer fields; avoid overflow at its API.
    if rate <= 0 or max(rate.numerator, rate.denominator) > 2**31 - 1:
        return None
    return rate
