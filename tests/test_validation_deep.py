from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

from tikrec.validation import validate_target


class DeepValidationTests(unittest.TestCase):
    def test_deep_mode_catches_a_decoder_error_that_standard_mode_skips(self) -> None:
        frame_calls = 0

        def runner(command: list[str], **_: object) -> object:
            nonlocal frame_calls
            if "-show_frames" in command:
                frame_calls += 1
                return SimpleNamespace(returncode=1, stderr="damaged final frame")
            document = {
                "streams": [
                    {"codec_type": "video", "codec_name": "h264", "width": 720, "height": 1280},
                    {"codec_type": "audio", "codec_name": "aac"},
                ],
                "format": {"format_name": "mov,mp4", "duration": "30"},
            }
            return SimpleNamespace(returncode=0, stdout=json.dumps(document), stderr="")

        with TemporaryDirectory() as temporary:
            output = Path(temporary) / "recording.mp4"
            output.write_bytes(b"media")
            standard = validate_target(output, runner=runner)
            deep = validate_target(output, deep=True, runner=runner)

        self.assertTrue(standard.passed)
        self.assertFalse(deep.passed)
        self.assertEqual(frame_calls, 1)
        self.assertIn("output_decode", [finding.code for finding in deep.findings])


if __name__ == "__main__":
    unittest.main()
