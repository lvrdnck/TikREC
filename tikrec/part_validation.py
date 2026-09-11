"""Low-level FFprobe validation for one retained TikREC FLV part."""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any


def validate_part(
    part: Path,
    ffprobe: str,
    runner: Callable[..., Any],
) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """Return hard failures and warnings found in one retained FLV part."""
    problems: list[tuple[str, str]] = []
    warnings: list[tuple[str, str]] = []
    decode_error = validate_decoding(part, ffprobe, runner)
    if decode_error is not None:
        problems.append(("decode", decode_error))

    packets = runner(
        [
            ffprobe,
            "-v",
            "error",
            "-show_packets",
            "-show_entries",
            "packet=stream_index,dts",
            "-of",
            "json",
            str(part),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    packet_error = (packets.stderr or "").strip()
    if packets.returncode or packet_error:
        problems.append(("DTS", _probe_failure(packets.returncode, packet_error)))
    else:
        try:
            warnings.extend(("DTS", warning) for warning in verify_packet_dts(packets.stdout))
        except (TypeError, ValueError, json.JSONDecodeError) as error:
            problems.append(("DTS", str(error)))
    return problems, warnings


def validate_decoding(
    media: Path,
    ffprobe: str,
    runner: Callable[..., Any],
) -> str | None:
    """Return the FFprobe decoder failure for one media file, if any."""
    decode = runner(
        [
            ffprobe,
            "-v",
            "error",
            "-show_frames",
            "-show_entries",
            "frame=media_type",
            "-of",
            "csv=p=0",
            str(media),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    output = (decode.stderr or "").strip()
    if decode.returncode or output:
        return _probe_failure(decode.returncode, output)
    return None


def verify_packet_dts(output: str) -> list[str]:
    """Return warnings for backward DTS jumps and reject invalid packet data."""
    document = json.loads(output)
    if not isinstance(document, dict) or not isinstance(document.get("packets"), list):
        raise ValueError("FFprobe returned malformed packet data")
    previous: dict[int, int] = {}
    stream_positions: dict[int, int] = {}
    warnings: list[str] = []
    for packet_number, packet in enumerate(document["packets"], start=1):
        if not isinstance(packet, dict):
            raise ValueError(f"packet {packet_number} is malformed")
        try:
            stream = int(packet["stream_index"])
            dts = int(packet["dts"])
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(f"packet {packet_number} has no valid stream/DTS") from error
        stream_positions[stream] = stream_positions.get(stream, 0) + 1
        if stream in previous and dts == previous[stream]:
            raise ValueError(
                f"stream {stream} DTS {dts} is not strictly greater than {previous[stream]}"
            )
        if stream in previous and dts < previous[stream]:
            warnings.append(
                f"stream {stream} packet {stream_positions[stream]} jumps backwards by "
                f"{previous[stream] - dts} ({previous[stream]} -> {dts})"
            )
        previous[stream] = dts
    return warnings


def _probe_failure(returncode: int, output: str) -> str:
    if output:
        return output
    return f"FFprobe exited with code {returncode}"
