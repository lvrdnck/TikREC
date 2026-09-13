"""Small, dependency-free helpers for FLV tags and AVC configuration data."""

from __future__ import annotations

from dataclasses import dataclass
from typing import BinaryIO

from .flv_codec import FlvFormatError, avc_configuration_dimensions, sps_dimensions


FLV_AUDIO_TAG = 8
FLV_VIDEO_TAG = 9
AVC_CODEC_ID = 7


@dataclass(frozen=True)
class FlvTag:
    """One complete FLV tag, excluding the FLV file header."""

    tag_type: int
    timestamp: int
    stream_id: bytes
    payload: bytes

    def __post_init__(self) -> None:
        if not 0 <= self.tag_type <= 0xFF:
            raise ValueError("FLV tag_type must fit in one byte")
        if not 0 <= self.timestamp <= 0xFFFFFFFF:
            raise ValueError("FLV timestamp must fit in four bytes")
        if len(self.stream_id) != 3:
            raise ValueError("FLV stream_id must contain exactly three bytes")

    @property
    def is_configuration(self) -> bool:
        """Whether this audio or video tag is a sequence/configuration packet."""
        return (
            self.tag_type in {FLV_AUDIO_TAG, FLV_VIDEO_TAG}
            and len(self.payload) >= 2
            and self.payload[1] == 0
        )

    @property
    def is_media(self) -> bool:
        """Whether this audio or video tag contains a raw media packet."""
        return (
            self.tag_type in {FLV_AUDIO_TAG, FLV_VIDEO_TAG}
            and len(self.payload) >= 2
            and self.payload[1] == 1
        )

    @property
    def is_avc_configuration(self) -> bool:
        """Whether this is an AVC video configuration packet."""
        return (
            self.tag_type == FLV_VIDEO_TAG
            and bool(self.payload)
            and (self.payload[0] & 0x0F) == AVC_CODEC_ID
            and self.is_configuration
        )

    def encoded(self, base_timestamp: int = 0) -> bytes:
        """Return this tag in its on-wire FLV form, rebased when requested."""
        if len(self.payload) > 0xFFFFFF:
            raise ValueError("FLV payload exceeds the three-byte size field")

        # A sequence header can precede the first media timestamp in a part.
        # FLV has unsigned timestamps, so that header is written at zero.
        timestamp = max(0, self.timestamp - base_timestamp)
        header = bytearray(11)
        header[0] = self.tag_type
        header[1:4] = len(self.payload).to_bytes(3, "big")
        header[4:7] = (timestamp & 0xFFFFFF).to_bytes(3, "big")
        # FLV stores the high timestamp byte after the low three bytes.
        header[7] = (timestamp >> 24) & 0xFF
        header[8:11] = self.stream_id
        previous_tag_size = (11 + len(self.payload)).to_bytes(4, "big")
        return bytes(header) + self.payload + previous_tag_size


def read_tag(stream: BinaryIO) -> FlvTag | None:
    """Read one complete tag, returning ``None`` only at a clean tag boundary."""
    header = _read_exact(stream, 11, allow_initial_eof=True)
    if header is None:
        return None

    payload_size = int.from_bytes(header[1:4], "big")
    payload = _read_exact(stream, payload_size)
    previous_tag_size = _read_exact(stream, 4)
    assert payload is not None and previous_tag_size is not None

    expected_size = 11 + payload_size
    if int.from_bytes(previous_tag_size, "big") != expected_size:
        raise FlvFormatError("FLV PreviousTagSize does not match its tag")

    # The timestamp extension is placed after, rather than before, its low bits.
    timestamp = int.from_bytes(header[4:7], "big") | (header[7] << 24)
    return FlvTag(header[0], timestamp, header[8:11], payload)


def _read_exact(
    stream: BinaryIO, count: int, *, allow_initial_eof: bool = False
) -> bytes | None:
    """Read exactly ``count`` bytes, including from short-reading HTTP streams."""
    chunks: list[bytes] = []
    remaining = count
    while remaining:
        chunk = stream.read(remaining)
        if not chunk:
            if allow_initial_eof and not chunks:
                return None
            raise EOFError(f"truncated FLV data: {remaining} bytes missing")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)
