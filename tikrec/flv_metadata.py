"""Read optional AMF0 onMetaData facts without affecting FLV capture."""

from __future__ import annotations

import math
import struct
from fractions import Fraction
from io import BytesIO


def metadata_values(payload: bytes) -> dict[str, object]:
    """Return an AMF0 metadata object, or no facts for unsupported/damaged data."""
    try:
        stream = BytesIO(payload)
        name = _value(stream, 0)
        if name == "@setDataFrame":
            name = _value(stream, 0)
        values = _value(stream, 0) if name == "onMetaData" else None
        return values if isinstance(values, dict) else {}
    except (ValueError, UnicodeError, struct.error):
        # Metadata is evidence only; an unfamiliar AMF type must not stop recording.
        return {}


def metadata_frame_rate(payload: bytes) -> str | None:
    """Return a positive rational publisher-advertised nominal frame rate."""
    value = metadata_values(payload).get("framerate")
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return None
    if not math.isfinite(value) or value <= 0:
        return None
    # AMF numbers are doubles; bound their rational form to avoid binary-float noise.
    rate = Fraction(str(value)).limit_denominator(1_000_000)
    if rate <= 0:
        return None  # Very small positive doubles can round to zero at the rational bound.
    return f"{rate.numerator}/{rate.denominator}"


def _read(stream: BytesIO, size: int) -> bytes:
    data = stream.read(size)
    if len(data) != size:
        raise ValueError("truncated AMF metadata")
    return data


def _string(stream: BytesIO, length_bytes: int = 2) -> str:
    length = int.from_bytes(_read(stream, length_bytes), "big")
    return _read(stream, length).decode("utf-8")


def _value(stream: BytesIO, depth: int) -> object:
    if depth > 8:
        raise ValueError("nested AMF metadata exceeds diagnostic limit")
    kind = _read(stream, 1)[0]
    if kind == 0:
        return struct.unpack(">d", _read(stream, 8))[0]
    if kind == 1:
        return bool(_read(stream, 1)[0])
    if kind in (2, 12):
        return _string(stream, 4 if kind == 12 else 2)
    if kind in (5, 6):
        return None
    if kind in (3, 8):
        if kind == 8:
            _read(stream, 4)  # ECMA array count is advisory; the object terminator wins.
        values: dict[str, object] = {}
        while True:
            name = _string(stream)
            if not name:
                position = stream.tell()
                if _read(stream, 1) == b"\x09":
                    return values
                stream.seek(position)  # An empty property name is legal before a value.
            values[name] = _value(stream, depth + 1)
    if kind == 10:
        count = int.from_bytes(_read(stream, 4), "big")
        if count > 10_000:
            raise ValueError("AMF array exceeds diagnostic limit")
        return [_value(stream, depth + 1) for _ in range(count)]
    if kind == 11:
        return struct.unpack(">d", _read(stream, 8))[0], _read(stream, 2)
    raise ValueError("unsupported AMF metadata type")
