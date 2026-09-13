"""Offline SPS diagnostics, including TikTok's non-fixed clock grid."""

import unittest

from tikrec.flv_codec import _BitReader, _vui_frame_rate, avc_configuration_facts
from tests.test_flv import BitWriter, make_avc_configuration, make_sps


class CodecFactsTests(unittest.TestCase):
    def test_dimensions_remain_available_without_timing(self):
        self.assertEqual(avc_configuration_facts(make_avc_configuration(make_sps(720, 1280))),
                         (720, 1280, None))

    def test_invalid_configuration_is_only_missing_evidence(self):
        self.assertEqual(avc_configuration_facts(b"broken"), (None, None, None))

    def test_nonfixed_tiktok_grid_is_not_a_nominal_rate(self):
        configuration = bytes.fromhex(
            "0164001fffe1001b6764001facd940b40a1a6a0c0c0c8000000300800003e8078c18cb"
            "01000668ebe2cb22c0fdf8f800")
        self.assertEqual(avc_configuration_facts(configuration), (720, 1280, None))

    def test_fixed_vui_rate_with_optional_fields(self):
        bits = BitWriter()
        bits.bits(1, 1)  # VUI present
        bits.bits(1, 1); bits.bits(255, 8); bits.bits(1, 16); bits.bits(1, 16)
        bits.bits(1, 1); bits.bits(0, 1)  # Overscan
        bits.bits(1, 1); bits.bits(0, 4); bits.bits(1, 1); bits.bits(0, 24)
        bits.bits(1, 1); bits.ue(0); bits.ue(0)  # Chroma locations
        bits.bits(1, 1); bits.bits(1001, 32); bits.bits(60000, 32); bits.bits(1, 1)
        self.assertEqual(str(_vui_frame_rate(_BitReader(bits.rbsp()))), "30000/1001")

    def test_fixed_vui_rate_is_extracted_from_complete_configuration(self):
        sps = make_sps(720, 1280)
        geometry = [int(bit) for byte in sps[1:] for bit in f"{byte:08b}"]
        bits = BitWriter()
        # Replace the fixture's RBSP stop bit/padding with VUI syntax and a new stop bit.
        bits._bits = geometry[:len(geometry) - 1 - geometry[::-1].index(1)]
        bits.bits(1, 1)  # VUI present
        bits.bits(0, 4)  # No aspect, overscan, video signal or chroma location fields.
        bits.bits(1, 1); bits.bits(1, 32); bits.bits(50, 32); bits.bits(1, 1)
        configuration = make_avc_configuration(b"\x67" + bits.rbsp())
        self.assertEqual(avc_configuration_facts(configuration), (720, 1280, "25/1"))


if __name__ == "__main__":
    unittest.main()
