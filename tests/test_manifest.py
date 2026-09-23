from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

from tikrec.manifest import SCHEMA_VERSION, SessionManifest
from tikrec.media import MediaInfo
from tikrec.decode_diagnostics import input_decode_health


def read_manifest(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


class SessionManifestTests(unittest.TestCase):
    def test_start_creates_a_versioned_recording_state(self) -> None:
        with TemporaryDirectory() as directory:
            parts = Path(directory) / "recording.parts"
            parts.mkdir()
            output = Path(directory) / "recording.mp4"
            manifest = SessionManifest(
                parts, output, "tiktok_live", clock=lambda: 100.25, session_id="session-123"
            )

            manifest.start(connection_count=1)
            values = read_manifest(parts / "session.json")

            self.assertEqual(values["schema_version"], SCHEMA_VERSION)
            self.assertEqual(values["session_id"], "session-123")
            self.assertEqual(values["tikrec_version"], "0.9.0")
            self.assertEqual(values["source_type"], "tiktok_live")
            self.assertEqual(values["started_at"], 100.25)
            self.assertEqual(values["status"], "recording")
            self.assertEqual(values["finalization"]["status"], "pending")
            self.assertFalse((parts / ".session.json.partial").exists())

    def test_finish_records_counts_timing_output_and_media(self) -> None:
        times = iter((100.0, 112.5))
        with TemporaryDirectory() as directory:
            root = Path(directory)
            parts = root / "recording.parts"
            parts.mkdir()
            retained = [parts / "part-0001.flv", parts / "part-0002.flv"]
            output = root / "recording.mp4"
            output.write_bytes(b"media")
            manifest = SessionManifest(
                parts,
                output,
                "direct_flv",
                clock=lambda: next(times),
                media_inspector=lambda _: MediaInfo("h264", "aac", 720, 1280),
            )
            manifest.start(connection_count=1)

            manifest.complete(
                retained,
                output_path=output,
                finalization_status="completed",
            )
            values = read_manifest(parts / "session.json")

        self.assertEqual(values["status"], "completed")
        self.assertEqual(values["ended_at"], 112.5)
        self.assertEqual(values["elapsed_seconds"], 12.5)
        self.assertEqual(values["part_count"], 2)
        self.assertEqual(values["connection_count"], 1)
        self.assertEqual(values["reconnect_count"], 0)
        self.assertEqual(values["output_path"], str(output))
        self.assertEqual(values["finalization"], {"status": "completed", "error": None})
        self.assertEqual(values["media"], {
            "video_codec": "h264", "audio_codec": "aac", "width": 720, "height": 1280,
        })

    def test_completed_manifest_keeps_separate_bounded_input_decode_health(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            parts = root / "recording.parts"
            parts.mkdir()
            output = root / "recording.mp4"
            output.write_bytes(b"media")
            manifest = SessionManifest(parts, output, "tiktok_live", clock=lambda: 1.0)
            manifest.start()
            manifest.complete([], output_path=output, finalization_status="completed",
                              input_decode=input_decode_health(
                                  "degraded", 1, ("h264_macroblock",)))
            values = read_manifest(parts / "session.json")
        self.assertEqual(values["status"], "completed")
        self.assertEqual(values["finalization"]["status"], "completed")
        self.assertEqual(values["finalization"]["input_decode"]["status"], "degraded")
        self.assertEqual(values["finalization"]["input_decode"]["diagnostic_count"], 1)

    def test_failure_keeps_optional_media_null_and_redacts_urls(self) -> None:
        times = iter((20.0, 21.0))
        with TemporaryDirectory() as directory:
            parts = Path(directory) / "recording.parts"
            parts.mkdir()
            manifest = SessionManifest(parts, None, "tag_stream", clock=lambda: next(times))
            manifest.start()

            manifest.fail([], "read failed at https://cdn.test/live.flv?token=secret")
            values = read_manifest(parts / "session.json")

        self.assertEqual(values["status"], "failed")
        self.assertEqual(values["error"], "read failed at [URL redacted]")
        self.assertEqual(values["finalization"]["status"], "not_requested")
        self.assertEqual(values["media"], {
            "video_codec": None, "audio_codec": None, "width": None, "height": None,
        })

    def test_failed_atomic_replace_preserves_the_previous_valid_manifest(self) -> None:
        with TemporaryDirectory() as directory:
            parts = Path(directory) / "recording.parts"
            parts.mkdir()
            manifest = SessionManifest(parts, None, "tag_stream", clock=lambda: 1.0)
            manifest.start()
            original = read_manifest(parts / "session.json")

            with patch("tikrec.manifest.os.replace", side_effect=OSError("disk failure")):
                with self.assertRaisesRegex(OSError, "disk failure"):
                    manifest.update_capture([parts / "part-0001.flv"])

            self.assertEqual(read_manifest(parts / "session.json"), original)
            self.assertFalse((parts / ".session.json.partial").exists())

    def test_recovery_updates_an_existing_manifest_without_rewriting_capture_time(self) -> None:
        times = iter((10.0, 15.0))
        with TemporaryDirectory() as directory:
            root = Path(directory)
            parts = root / "recording.parts"
            parts.mkdir()
            retained = [parts / "part-0001.flv"]
            manifest = SessionManifest(parts, None, "tiktok_live", clock=lambda: next(times))
            manifest.start(connection_count=2)
            manifest.complete(retained, interrupted=True)
            output = root / "recovered.mp4"
            output.write_bytes(b"media")

            loaded = SessionManifest.load(
                parts / "session.json",
                media_inspector=lambda _: MediaInfo("h264", "aac", 1080, 1920),
            )
            assert loaded is not None
            loaded.mark_recovery(output, retained)
            loaded.finish_recovery(retained, "completed", output_path=output)
            values = read_manifest(parts / "session.json")

        self.assertEqual(values["status"], "interrupted")
        self.assertEqual(values["ended_at"], 15.0)
        self.assertEqual(values["elapsed_seconds"], 5.0)
        self.assertTrue(values["recovery_performed"])
        self.assertEqual(values["finalization"]["status"], "completed")


if __name__ == "__main__":
    unittest.main()
