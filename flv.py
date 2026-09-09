"""Small, dependency-free helpers for FLV tags and AVC configuration data."""

from __future__ import annotations

from dataclasses import dataclass
from typing import BinaryIO


FLV_AUDIO_TAG = 8
FLV_VIDEO_TAG = 9
AVC_CODEC_ID = 7


class FlvFormatError(ValueError):
    """Raised when bytes do not form the FLV or AVC structure being parsed."""


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
        header[7] = timestamp >> 24
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


class _BitReader:
    """Read H.264 syntax elements from an RBSP bit stream."""

    def __init__(self, data: bytes) -> None:
        self._data = data
        self._position = 0

    def read(self, count: int) -> int:
        if count < 0 or self._position + count > len(self._data) * 8:
            raise FlvFormatError("truncated H.264 SPS")
        value = 0
        for _ in range(count):
            byte = self._data[self._position // 8]
            value = (value << 1) | ((byte >> (7 - self._position % 8)) & 1)
            self._position += 1
        return value

    def unsigned_exp_golomb(self) -> int:
        """Read the unsigned Exp-Golomb values used by H.264 SPS fields."""
        leading_zeros = 0
        while self.read(1) == 0:
            leading_zeros += 1
            if leading_zeros > 31:
                raise FlvFormatError("invalid H.264 Exp-Golomb value")
        suffix = self.read(leading_zeros) if leading_zeros else 0
        return (1 << leading_zeros) - 1 + suffix

    def signed_exp_golomb(self) -> int:
        value = self.unsigned_exp_golomb()
        return (value + 1) // 2 if value & 1 else -(value // 2)


def sps_dimensions(sps: bytes) -> tuple[int, int]:
    """Extract the displayed width and height from an H.264 SPS NAL unit."""
    if not sps or (sps[0] & 0x1F) != 7:
        raise FlvFormatError("expected an H.264 SPS NAL unit")

    reader = _BitReader(_rbsp_without_emulation_bytes(sps[1:]))
    profile_idc = reader.read(8)
    reader.read(8)  # Constraint flags occupy this byte in every SPS profile.
    reader.read(8)  # level_idc does not affect the coded frame dimensions.
    reader.unsigned_exp_golomb()  # seq_parameter_set_id

    chroma_format_idc = 1
    separate_colour_plane_flag = 0
    if profile_idc in _HIGH_PROFILE_IDS:
        chroma_format_idc = reader.unsigned_exp_golomb()
        if chroma_format_idc > 3:
            raise FlvFormatError("invalid H.264 chroma_format_idc")
        if chroma_format_idc == 3:
            separate_colour_plane_flag = reader.read(1)
        reader.unsigned_exp_golomb()  # bit_depth_luma_minus8
        reader.unsigned_exp_golomb()  # bit_depth_chroma_minus8
        reader.read(1)  # qpprime_y_zero_transform_bypass_flag
        if reader.read(1):
            _skip_scaling_matrices(reader, chroma_format_idc)

    reader.unsigned_exp_golomb()  # log2_max_frame_num_minus4
    pic_order_cnt_type = reader.unsigned_exp_golomb()
    if pic_order_cnt_type == 0:
        reader.unsigned_exp_golomb()  # log2_max_pic_order_cnt_lsb_minus4
    elif pic_order_cnt_type == 1:
        reader.read(1)  # delta_pic_order_always_zero_flag
        reader.signed_exp_golomb()  # offset_for_non_ref_pic
        reader.signed_exp_golomb()  # offset_for_top_to_bottom_field
        for _ in range(reader.unsigned_exp_golomb()):
            reader.signed_exp_golomb()
    elif pic_order_cnt_type != 2:
        raise FlvFormatError("invalid H.264 pic_order_cnt_type")

    reader.unsigned_exp_golomb()  # max_num_ref_frames
    reader.read(1)  # gaps_in_frame_num_value_allowed_flag
    width_in_mbs = reader.unsigned_exp_golomb() + 1
    height_in_map_units = reader.unsigned_exp_golomb() + 1
    frame_mbs_only_flag = reader.read(1)
    if not frame_mbs_only_flag:
        reader.read(1)  # mb_adaptive_frame_field_flag exists for interlacing.
    reader.read(1)  # direct_8x8_inference_flag

    crop_left = crop_right = crop_top = crop_bottom = 0
    if reader.read(1):
        crop_left = reader.unsigned_exp_golomb()
        crop_right = reader.unsigned_exp_golomb()
        crop_top = reader.unsigned_exp_golomb()
        crop_bottom = reader.unsigned_exp_golomb()

    chroma_array_type = 0 if separate_colour_plane_flag else chroma_format_idc
    crop_unit_x, crop_unit_y = _crop_units(
        chroma_array_type, frame_mbs_only_flag
    )
    width = width_in_mbs * 16 - crop_unit_x * (crop_left + crop_right)
    height = (
        (2 - frame_mbs_only_flag) * height_in_map_units * 16
        - crop_unit_y * (crop_top + crop_bottom)
    )
    if width <= 0 or height <= 0:
        raise FlvFormatError("H.264 SPS cropping produces invalid dimensions")
    return width, height


def avc_configuration_dimensions(configuration: bytes) -> tuple[int, int]:
    """Extract dimensions from an AVCDecoderConfigurationRecord's first SPS."""
    if len(configuration) < 7 or configuration[0] != 1:
        raise FlvFormatError("invalid AVCDecoderConfigurationRecord")

    position = 6
    sps_count = configuration[5] & 0x1F
    if not sps_count:
        raise FlvFormatError("AVC configuration contains no SPS")

    first_sps: bytes | None = None
    for _ in range(sps_count):
        sps, position = _read_length_prefixed_nal(configuration, position)
        if first_sps is None:
            first_sps = sps

    if position >= len(configuration):
        raise FlvFormatError("AVC configuration is missing its PPS count")
    pps_count = configuration[position]
    position += 1
    for _ in range(pps_count):
        _, position = _read_length_prefixed_nal(configuration, position)

    assert first_sps is not None
    return sps_dimensions(first_sps)


def _read_length_prefixed_nal(data: bytes, position: int) -> tuple[bytes, int]:
    if position + 2 > len(data):
        raise FlvFormatError("truncated AVC NAL length")
    length = int.from_bytes(data[position : position + 2], "big")
    position += 2
    if not length or position + length > len(data):
        raise FlvFormatError("truncated AVC NAL data")
    return data[position : position + length], position + length


def _rbsp_without_emulation_bytes(data: bytes) -> bytes:
    """Remove H.264's 00 00 03 escape bytes before reading SPS bits."""
    output = bytearray()
    zero_count = 0
    for byte in data:
        if zero_count >= 2 and byte == 3:
            zero_count = 0
            continue
        output.append(byte)
        zero_count = zero_count + 1 if byte == 0 else 0
    return bytes(output)


def _skip_scaling_matrices(reader: _BitReader, chroma_format_idc: int) -> None:
    count = 8 if chroma_format_idc != 3 else 12
    for index in range(count):
        if reader.read(1):
            _skip_scaling_list(reader, 16 if index < 6 else 64)


def _skip_scaling_list(reader: _BitReader, length: int) -> None:
    last_scale = next_scale = 8
    for _ in range(length):
        if next_scale:
            next_scale = (last_scale + reader.signed_exp_golomb() + 256) % 256
        last_scale = next_scale or last_scale


def _crop_units(
    chroma_array_type: int, frame_mbs_only_flag: int
) -> tuple[int, int]:
    if chroma_array_type == 0:
        return 1, 2 - frame_mbs_only_flag
    sub_width = 1 if chroma_array_type == 3 else 2
    sub_height = 2 if chroma_array_type == 1 else 1
    return sub_width, sub_height * (2 - frame_mbs_only_flag)


_HIGH_PROFILE_IDS = frozenset(
    {44, 83, 86, 100, 110, 118, 122, 128, 134, 135, 138, 139, 244}
)
