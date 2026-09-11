from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
import unittest

from tikrec.media import MediaInfo, inspect_media


class MediaInspectionTests(unittest.TestCase):
    def test_extracts_codec_and_resolution_from_ffprobe_streams(self) -> None:
        document = {
            "streams": [
                {"codec_type": "video", "codec_name": "h264", "width": 720, "height": 1280},
                {"codec_type": "audio", "codec_name": "aac"},
            ]
        }
        commands: list[list[str]] = []

        def runner(command: list[str], **_: object) -> object:
            commands.append(command)
            return SimpleNamespace(returncode=0, stdout=json.dumps(document))

        result = inspect_media(Path("recording.mp4"), ffprobe="probe", runner=runner)

        self.assertEqual(result, MediaInfo("h264", "aac", 720, 1280))
        self.assertEqual(commands[0][0], "probe")
        self.assertIn("-show_streams", commands[0])

    def test_probe_failure_returns_no_optional_media_information(self) -> None:
        def runner(*_: object, **__: object) -> object:
            return SimpleNamespace(returncode=1, stdout="not json")

        self.assertIsNone(inspect_media(Path("recording.mp4"), runner=runner))


if __name__ == "__main__":
    unittest.main()
