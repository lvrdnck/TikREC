"""Bounded, fixed-code evidence from FFmpeg input decoder messages."""

from __future__ import annotations

import re


_MAX_COUNT = 10000
_H264 = re.compile(r"^\[h264 @ (?:0x)?[0-9a-fA-F]+\]\s*(.*)$")
_CODES = frozenset({
    "h264_intra_prediction", "h264_macroblock", "h264_reference",
    "h264_entropy", "h264_bitstream", "h264_concealment", "decode_pipeline",
})
_STATUSES = frozenset({"clean", "degraded", "not_checked", "unknown"})


def input_decode_health(status: str, count: int = 0,
                        codes: tuple[str, ...] = (), capped: bool = False) -> dict:
    """Construct fixed, JSON-safe input-decoder evidence without raw stderr."""
    value = {"status": status, "diagnostic_count": count,
             "diagnostic_codes": sorted(set(codes)), "count_capped": capped}
    if not valid_input_decode_health(value):
        raise ValueError("invalid input decoder evidence")
    return value


def valid_input_decode_health(value: object) -> bool:
    """Accept only the bounded evidence schema, including after disk reads."""
    if not isinstance(value, dict) or set(value) != {
        "status", "diagnostic_count", "diagnostic_codes", "count_capped",
    }:
        return False
    status = value["status"]
    count = value["diagnostic_count"]
    codes = value["diagnostic_codes"]
    capped = value["count_capped"]
    if (not isinstance(status, str) or not isinstance(codes, list)
            or not all(isinstance(code, str) for code in codes)):
        return False
    return (
        status in _STATUSES and type(count) is int and 0 <= count <= _MAX_COUNT
        and type(capped) is bool
        and codes == sorted(set(codes)) and set(codes) <= _CODES
        and ((status == "degraded" and count > 0 and bool(codes))
             or (status != "degraded" and count == 0 and not codes and not capped))
        and (not capped or count == _MAX_COUNT)
    )


def safe_input_decode_health(value: object) -> dict:
    """Return only verified fixed fields to service consumers."""
    if not valid_input_decode_health(value):
        return input_decode_health("unknown")
    return {**value, "diagnostic_codes": list(value["diagnostic_codes"])}


class DecodeDiagnostics:
    """Classify meaningful FFmpeg decoder lines without retaining their text."""

    def __init__(self) -> None:
        self._count = 0
        self._capped = False
        self._codes: set[str] = set()

    def observe(self, line: str) -> None:
        """Add a fixed code for a known decoder failure, ignoring other stderr."""
        code = classify_decoder_line(line)
        if code is None:
            return
        self._codes.add(code)
        if self._count < _MAX_COUNT:
            self._count += 1
        else:
            self._capped = True

    def result(self) -> dict:
        """Return clean/degraded health based on classified input messages."""
        return input_decode_health(
            "degraded" if self._codes else "clean", self._count,
            tuple(self._codes), self._capped,
        )


def classify_decoder_line(line: str) -> str | None:
    """Map recognized H.264 input failures to allowlisted stable codes."""
    match = _H264.match(line.strip())
    if match is None:
        return "decode_pipeline" if "Error while decoding stream #" in line else None
    message = match.group(1).lower()
    # FFmpeg's repeated Late SEI notice describes unsupported optional metadata.
    if "late sei is not implemented" in message:
        return None
    if "left block unavailable" in message:
        return "h264_intra_prediction"
    if "error while decoding mb" in message:
        return "h264_macroblock"
    if re.search(r"reference \d+ >= \d+", message):
        return "h264_reference"
    if "cabac decode" in message:
        return "h264_entropy"
    if any(token in message for token in (
        "invalid nal", "non-existing pps", "sps unavailable",
        "decode_slice_header error", "corrupt",
    )):
        return "h264_bitstream"
    if "concealing" in message:
        return "h264_concealment"
    return None
