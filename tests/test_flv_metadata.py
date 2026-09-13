"""Offline fixtures for optional publisher metadata."""

import struct
import unittest

from tikrec.flv_metadata import metadata_frame_rate, metadata_values


def amf_string(value: str) -> bytes:
    encoded = value.encode()
    return b"\x02" + len(encoded).to_bytes(2, "big") + encoded


def metadata(rate: float, *, ecma: bool = False) -> bytes:
    header = b"\x08\x00\x00\x00\x01" if ecma else b"\x03"
    return (amf_string("onMetaData") + header + b"\x00\x09framerate\x00"
            + struct.pack(">d", rate) + b"\x00\x00\x09")


class MetadataTests(unittest.TestCase):
    def test_object_and_ecma_array_rates(self):
        for ecma in (False, True):
            self.assertEqual(metadata_frame_rate(metadata(25, ecma=ecma)), "25/1")

    def test_set_data_frame_and_fractional_rate(self):
        self.assertEqual(metadata_frame_rate(amf_string("@setDataFrame") + metadata(29.97)),
                         "2997/100")

    def test_nonpositive_and_nonfinite_rates_are_unknown(self):
        for rate in (0, -1, 1e-300, float("nan"), float("inf")):
            self.assertIsNone(metadata_frame_rate(metadata(rate)))

    def test_truncated_and_unrelated_metadata_are_ignored(self):
        for payload in (metadata(15)[:-1], b"broken", amf_string("unrelated")):
            self.assertEqual(metadata_values(payload), {})
            self.assertIsNone(metadata_frame_rate(payload))

    def test_strings_booleans_nested_objects_and_unknown_types(self):
        payload = (amf_string("onMetaData") + b"\x03\x00\x04name" + amf_string("hd")
                   + b"\x00\x04flag\x01\x01\x00\x06nested\x03\x00\x00\x09"
                   + b"\x00\x00\x09")
        self.assertEqual(metadata_values(payload), {"name": "hd", "flag": True, "nested": {}})
        self.assertIsNone(metadata_frame_rate(payload))
        self.assertEqual(metadata_values(amf_string("onMetaData") + b"\x04"), {})


if __name__ == "__main__":
    unittest.main()
