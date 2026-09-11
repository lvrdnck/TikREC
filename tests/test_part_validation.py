from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
import unittest

from tikrec.part_validation import validate_decoding, validate_part, verify_packet_dts


class PartValidationTests(unittest.TestCase):
    def test_clean_part_passes_decode_and_packet_checks(self) -> None:
        def runner(command, **_: object):
            if "-show_packets" in command:
                packets = {"packets": [{"stream_index": 0, "dts": 0}]}
                return SimpleNamespace(returncode=0, stdout=json.dumps(packets), stderr="")
            return SimpleNamespace(returncode=0, stderr="")

        problems, warnings = validate_part(Path("part-0001.flv"), "ffprobe", runner)

        self.assertEqual(problems, [])
        self.assertEqual(warnings, [])

    def test_decode_failure_is_reported(self) -> None:
        def runner(command, **_: object):
            if "-show_frames" in command:
                return SimpleNamespace(returncode=1, stderr="invalid media")
            return SimpleNamespace(returncode=0, stdout='{"packets": []}', stderr="")

        problems, _ = validate_part(Path("part-0001.flv"), "ffprobe", runner)

        self.assertIn(("decode", "invalid media"), problems)

    def test_decoder_check_is_reusable_for_a_completed_output(self) -> None:
        def runner(*_: object, **__: object):
            return SimpleNamespace(returncode=0, stderr="")

        self.assertIsNone(validate_decoding(Path("recording.mp4"), "ffprobe", runner))

    def test_backward_dts_is_a_warning_but_duplicate_is_invalid(self) -> None:
        backward = json.dumps({"packets": [
            {"stream_index": 0, "dts": 20},
            {"stream_index": 0, "dts": 10},
        ]})
        duplicate = json.dumps({"packets": [
            {"stream_index": 0, "dts": 10},
            {"stream_index": 0, "dts": 10},
        ]})

        self.assertEqual(len(verify_packet_dts(backward)), 1)
        with self.assertRaisesRegex(ValueError, "not strictly greater"):
            verify_packet_dts(duplicate)


if __name__ == "__main__":
    unittest.main()
