from __future__ import annotations

import json
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

from scripts.validate_parts import validate_parts


class ValidatePartsCompatibilityTests(unittest.TestCase):
    def test_wrapper_uses_supported_validator_and_custom_ffprobe(self) -> None:
        commands: list[list[str]] = []

        def runner(command: list[str], **_: object) -> object:
            commands.append(command)
            if "-show_packets" in command:
                return SimpleNamespace(
                    returncode=0,
                    stdout=json.dumps({"packets": [{"stream_index": 0, "dts": 0}]}),
                    stderr="",
                )
            if "-show_frames" in command:
                return SimpleNamespace(returncode=0, stdout="video\n", stderr="")
            media = {
                "streams": [{
                    "codec_type": "video", "codec_name": "h264", "width": 720, "height": 1280,
                }],
                "format": {"format_name": "flv", "duration": "1"},
            }
            return SimpleNamespace(returncode=0, stdout=json.dumps(media), stderr="")

        with TemporaryDirectory() as temporary:
            directory = Path(temporary) / "recording.parts"
            directory.mkdir()
            (directory / "part-0001.flv").write_bytes(b"media")
            stdout = StringIO()
            code = validate_parts(
                directory, ffprobe="custom-probe", runner=runner, stdout=stdout
            )

        self.assertEqual(code, 0)
        self.assertTrue(all(command[0] == "custom-probe" for command in commands))
        self.assertIn("Validation passed", stdout.getvalue())

    def test_wrapper_returns_one_for_a_validation_failure(self) -> None:
        stdout = StringIO()

        code = validate_parts(Path("missing.parts"), stdout=stdout)

        self.assertEqual(code, 1)
        self.assertIn("[target_missing]", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
