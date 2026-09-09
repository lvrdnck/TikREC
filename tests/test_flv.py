from __future__ import annotations

from io import BytesIO
import unittest

from flv import (
    FlvFormatError,
    FlvTag,
    avc_configuration_dimensions,
    read_tag,
    sps_dimensions,
)


class ShortReadStream:
    """A stream that returns small chunks, like an HTTP response can."""

    def __init__(self, data: bytes, chunk_size: int) -> None:
        self._data = data
        self._chunk_size = chunk_size
        self._position = 0

    def read(self, count: int) -> bytes:
        size = min(count, self._chunk_size)
        chunk = self._data[self._position : self._position + size]
        self._position += len(chunk)
        return chunk


class BitWriter:
    def __init__(self) -> None:
        self._bits: list[int] = []

    def bits(self, value: int, count: int) -> None:
        self._bits.extend((value >> shift) & 1 for shift in range(count - 1, -1, -1))

    def ue(self, value: int) -> None:
        code_num = value + 1
        width = code_num.bit_length()
        self.bits(0, width - 1)
        self.bits(code_num, width)

    def rbsp(self) -> bytes:
        self._bits.append(1)  # rbsp_stop_one_bit terminates the SPS syntax.
        while len(self._bits) % 8:
            self._bits.append(0)
        return bytes(
            sum(self._bits[offset + bit] << (7 - bit) for bit in range(8))
            for offset in range(0, len(self._bits), 8)
        )


def make_sps(width: int, height: int) -> bytes:
    """Make a small, valid High Profile 4:2:0 SPS for dimension tests."""
    if width % 2 or height % 2:
        raise ValueError("4:2:0 test dimensions must be even")
    width_in_mbs = (width + 15) // 16
    height_in_map_units = (height + 15) // 16
    crop_right = (width_in_mbs * 16 - width) // 2
    crop_bottom = (height_in_map_units * 16 - height) // 2

    writer = BitWriter()
    writer.bits(100, 8)  # profile_idc: High, so chroma syntax is present.
    writer.bits(0, 8)  # constraint flags and reserved bits
    writer.bits(31, 8)  # level_idc
    writer.ue(0)  # seq_parameter_set_id
    writer.ue(1)  # chroma_format_idc: 4:2:0
    writer.ue(0)  # bit_depth_luma_minus8
    writer.ue(0)  # bit_depth_chroma_minus8
    writer.bits(0, 1)  # qpprime_y_zero_transform_bypass_flag
    writer.bits(0, 1)  # seq_scaling_matrix_present_flag
    writer.ue(0)  # log2_max_frame_num_minus4
    writer.ue(0)  # pic_order_cnt_type
    writer.ue(0)  # log2_max_pic_order_cnt_lsb_minus4
    writer.ue(1)  # max_num_ref_frames
    writer.bits(0, 1)  # gaps_in_frame_num_value_allowed_flag
    writer.ue(width_in_mbs - 1)
    writer.ue(height_in_map_units - 1)
    writer.bits(1, 1)  # frame_mbs_only_flag: progressive frame
    writer.bits(1, 1)  # direct_8x8_inference_flag
    writer.bits(1 if crop_right or crop_bottom else 0, 1)
    if crop_right or crop_bottom:
        writer.ue(0)  # frame_crop_left_offset
        writer.ue(crop_right)
        writer.ue(0)  # frame_crop_top_offset
        writer.ue(crop_bottom)
    return bytes([0x67]) + writer.rbsp()


def make_avc_configuration(sps: bytes) -> bytes:
    pps = b"\x68\x00"
    return (
        b"\x01\x64\x00\x1f\xff\xe1"
        + len(sps).to_bytes(2, "big")
        + sps
        + b"\x01"
        + len(pps).to_bytes(2, "big")
        + pps
    )


class FlvTagTests(unittest.TestCase):
    def test_round_trip_preserves_extended_timestamp_through_short_reads(self) -> None:
        original = FlvTag(9, 0x01020304, b"\x00\x00\x00", b"\x17\x01frame")

        decoded = read_tag(ShortReadStream(original.encoded(), chunk_size=3))

        self.assertEqual(decoded, original)
        self.assertTrue(decoded.is_media)
        self.assertFalse(decoded.is_configuration)

    def test_encoded_tag_rebases_a_earlier_configuration_to_zero(self) -> None:
        tag = FlvTag(9, 50, b"\x00\x00\x00", b"\x17\x00config")

        decoded = read_tag(BytesIO(tag.encoded(base_timestamp=100)))

        self.assertEqual(decoded.timestamp, 0)
        self.assertTrue(decoded.is_configuration)
        self.assertTrue(decoded.is_avc_configuration)

    def test_clean_end_returns_none_but_a_torn_tag_raises_eof_error(self) -> None:
        self.assertIsNone(read_tag(BytesIO()))
        torn_tag = FlvTag(8, 0, b"\x00\x00\x00", b"\xaf\x01audio").encoded()[:-2]

        with self.assertRaises(EOFError):
            read_tag(BytesIO(torn_tag))

    def test_rejects_an_incorrect_previous_tag_size(self) -> None:
        encoded = bytearray(FlvTag(9, 0, b"\x00\x00\x00", b"x").encoded())
        encoded[-1] += 1

        with self.assertRaises(FlvFormatError):
            read_tag(BytesIO(encoded))


class AvcDimensionsTests(unittest.TestCase):
    def test_sps_dimensions_apply_4_2_0_cropping(self) -> None:
        self.assertEqual(sps_dimensions(make_sps(854, 480)), (854, 480))

    def test_avc_configuration_uses_its_sps_dimensions(self) -> None:
        configuration = make_avc_configuration(make_sps(720, 1280))

        self.assertEqual(avc_configuration_dimensions(configuration), (720, 1280))

    def test_rejects_truncated_avc_configuration(self) -> None:
        with self.assertRaises(FlvFormatError):
            avc_configuration_dimensions(b"\x01\x64\x00\x1f\xff\xe1\x00")


if __name__ == "__main__":
    unittest.main()
