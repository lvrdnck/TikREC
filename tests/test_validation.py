from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

from tikrec.validation import validate_target


class ProbeRunner:
    def __init__(self) -> None:
        self.decode_errors: dict[str, str] = {}
        self.packet_documents: dict[str, object] = {}
        self.media_documents: dict[str, object] = {}

    def __call__(self, command: list[str], **_: object) -> object:
        name = Path(command[-1]).name
        if "-show_frames" in command:
            error = self.decode_errors.get(name, "")
            return SimpleNamespace(returncode=bool(error), stdout="video\naudio\n", stderr=error)
        if "-show_packets" in command:
            document = self.packet_documents.get(
                name,
                {"packets": [
                    {"stream_index": 0, "dts": 0},
                    {"stream_index": 1, "dts": 0},
                    {"stream_index": 0, "dts": 40},
                ]},
            )
            return SimpleNamespace(returncode=0, stdout=json.dumps(document), stderr="")
        document = self.media_documents.get(name, {
            "streams": [
                {"codec_type": "video", "codec_name": "h264", "width": 720, "height": 1280},
                {"codec_type": "audio", "codec_name": "aac"},
            ],
            "format": {"format_name": "flv", "duration": "12.5"},
        })
        return SimpleNamespace(returncode=0, stdout=json.dumps(document), stderr="")


def write_part(directory: Path, name: str = "part-0001.flv") -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    part = directory / name
    part.write_bytes(b"media")
    return part


def manifest_values(directory: Path, output: Path | None, **changes: object) -> dict[str, object]:
    values: dict[str, object] = {
        "schema_version": 1,
        "status": "completed",
        "parts_directory": str(directory),
        "output_path": None if output is None else str(output),
        "part_count": 1,
        "finalization": {"status": "completed", "error": None},
        "media": {"video_codec": "h264", "audio_codec": "aac", "width": 720, "height": 1280},
    }
    values.update(changes)
    return values


class ValidationTests(unittest.TestCase):
    def test_healthy_legacy_parts_pass_with_unknown_session_state(self) -> None:
        with TemporaryDirectory() as temporary:
            directory = Path(temporary) / "old.parts"
            write_part(directory)
            result = validate_target(directory, runner=ProbeRunner())

        self.assertTrue(result.passed)
        self.assertEqual(result.target_type, "parts")
        self.assertEqual(result.media_integrity, "passed")
        self.assertEqual(result.session_completeness, "unknown")
        self.assertIn("manifest_missing", [finding.code for finding in result.findings])

    def test_corrupt_part_collects_decode_and_dts_failures(self) -> None:
        runner = ProbeRunner()
        runner.decode_errors["part-0001.flv"] = "AAC decode error"
        runner.packet_documents["part-0001.flv"] = {
            "packets": [
                {"stream_index": 0, "dts": 10},
                {"stream_index": 0, "dts": 10},
            ]
        }
        with TemporaryDirectory() as temporary:
            directory = Path(temporary) / "bad.parts"
            write_part(directory)
            result = validate_target(directory, runner=runner)

        self.assertFalse(result.passed)
        self.assertEqual(result.media_integrity, "failed")
        self.assertTrue({"part_decode", "part_dts"}.issubset(
            {finding.code for finding in result.findings}
        ))

    def test_empty_and_non_file_parts_are_reported_without_probing(self) -> None:
        with TemporaryDirectory() as temporary:
            directory = Path(temporary) / "bad.parts"
            directory.mkdir()
            (directory / "part-0001.flv").write_bytes(b"")
            (directory / "part-0002.flv").mkdir()
            result = validate_target(directory, runner=ProbeRunner())

        self.assertFalse(result.passed)
        self.assertEqual(result.parts_checked, 2)
        self.assertEqual(
            [finding.code for finding in result.findings].count("part_unreadable"), 2
        )

    def test_healthy_completed_output_passes(self) -> None:
        with TemporaryDirectory() as temporary:
            output = Path(temporary) / "recording.mp4"
            output.write_bytes(b"media")
            result = validate_target(output, runner=ProbeRunner())

        self.assertTrue(result.passed)
        self.assertEqual(result.target_type, "output")
        self.assertEqual(result.media_integrity, "passed")
        self.assertEqual(result.output_availability, "present")

    def test_broken_completed_output_fails_probe(self) -> None:
        class BrokenProbe:
            def __call__(self, *_: object, **__: object) -> object:
                return SimpleNamespace(returncode=1, stdout="not json", stderr="bad")

        with TemporaryDirectory() as temporary:
            output = Path(temporary) / "recording.mp4"
            output.write_bytes(b"broken")
            result = validate_target(output, runner=BrokenProbe())

        self.assertFalse(result.passed)
        self.assertIn("output_probe_failed", [finding.code for finding in result.findings])

    def test_complete_session_checks_parts_output_and_manifest(self) -> None:
        with TemporaryDirectory() as temporary:
            directory = Path(temporary) / "recording.parts"
            output = Path(temporary) / "recording.mp4"
            write_part(directory)
            output.write_bytes(b"media")
            (directory / "session.json").write_text(
                json.dumps(manifest_values(directory, output)), encoding="utf-8"
            )
            runner = ProbeRunner()
            runner.media_documents["recording.mp4"] = {
                "streams": [
                    {"codec_type": "video", "codec_name": "h264", "width": 720, "height": 1280},
                    {"codec_type": "audio", "codec_name": "aac"},
                ],
                "format": {"format_name": "mov,mp4", "duration": "10"},
            }
            result = validate_target(directory / "session.json", runner=runner)

        self.assertTrue(result.passed)
        self.assertEqual(result.target_type, "session")
        self.assertEqual(result.session_completeness, "complete")
        self.assertEqual(result.parts_checked, 1)

    def test_manifest_inconsistencies_are_collected(self) -> None:
        with TemporaryDirectory() as temporary:
            directory = Path(temporary) / "recording.parts"
            missing_output = Path(temporary) / "missing.mp4"
            write_part(directory)
            values = manifest_values(directory, missing_output, part_count=4)
            (directory / "session.json").write_text(json.dumps(values), encoding="utf-8")
            result = validate_target(directory, runner=ProbeRunner())

        codes = {finding.code for finding in result.findings}
        self.assertFalse(result.passed)
        self.assertTrue({"manifest_part_count_mismatch", "output_missing"}.issubset(codes))

    def test_missing_optional_manifest_media_is_not_a_failure(self) -> None:
        with TemporaryDirectory() as temporary:
            directory = Path(temporary) / "recording.parts"
            output = Path(temporary) / "recording.mp4"
            write_part(directory)
            output.write_bytes(b"media")
            values = manifest_values(directory, output, media={
                "video_codec": None, "audio_codec": None, "width": None, "height": None,
            })
            (directory / "session.json").write_text(json.dumps(values), encoding="utf-8")
            result = validate_target(directory, runner=ProbeRunner())

        self.assertTrue(result.passed)

    def test_manifest_media_mismatch_fails_consistency(self) -> None:
        with TemporaryDirectory() as temporary:
            directory = Path(temporary) / "recording.parts"
            output = Path(temporary) / "recording.mp4"
            write_part(directory)
            output.write_bytes(b"media")
            values = manifest_values(directory, output, media={"video_codec": "hevc"})
            (directory / "session.json").write_text(json.dumps(values), encoding="utf-8")
            result = validate_target(directory, runner=ProbeRunner())

        self.assertFalse(result.passed)
        self.assertIn("manifest_media_mismatch", [finding.code for finding in result.findings])

    def test_malformed_manifest_fails_but_retained_parts_are_still_checked(self) -> None:
        with TemporaryDirectory() as temporary:
            directory = Path(temporary) / "recording.parts"
            write_part(directory)
            (directory / "session.json").write_text("{broken", encoding="utf-8")
            result = validate_target(directory, runner=ProbeRunner())

        self.assertFalse(result.passed)
        self.assertEqual(result.parts_checked, 1)
        self.assertEqual(result.media_integrity, "passed")
        self.assertIn("manifest_unreadable", [finding.code for finding in result.findings])

    def test_interrupted_session_with_healthy_parts_is_not_called_corrupt(self) -> None:
        with TemporaryDirectory() as temporary:
            directory = Path(temporary) / "recording.parts"
            output = Path(temporary) / "recording.mp4"
            write_part(directory)
            values = manifest_values(
                directory, output, status="interrupted",
                finalization={"status": "not_started", "error": None},
            )
            (directory / "session.json").write_text(json.dumps(values), encoding="utf-8")
            result = validate_target(directory, runner=ProbeRunner())

        self.assertTrue(result.passed)
        self.assertEqual(result.media_integrity, "passed")
        self.assertEqual(result.session_completeness, "interrupted")
        self.assertEqual(result.output_availability, "missing")

    def test_missing_target_is_a_validation_failure(self) -> None:
        result = validate_target(Path("definitely-does-not-exist"), runner=ProbeRunner())

        self.assertFalse(result.passed)
        self.assertEqual(result.target_type, "missing")
        self.assertIn("target_missing", [finding.code for finding in result.findings])

    def test_invalid_output_streams_and_duration_are_collected(self) -> None:
        runner = ProbeRunner()
        runner.media_documents["recording.mp4"] = {
            "streams": [], "format": {"format_name": "mov,mp4", "duration": "0"},
        }
        with TemporaryDirectory() as temporary:
            output = Path(temporary) / "recording.mp4"
            output.write_bytes(b"media")
            result = validate_target(output, runner=runner)

        codes = {finding.code for finding in result.findings}
        self.assertFalse(result.passed)
        self.assertTrue({"output_video_missing", "output_duration_invalid"}.issubset(codes))
        self.assertIn("output_audio_missing", codes)

    def test_ffprobe_execution_failure_is_reported_for_a_part(self) -> None:
        def unavailable(*_: object, **__: object) -> object:
            raise OSError("ffprobe not installed")

        with TemporaryDirectory() as temporary:
            directory = Path(temporary) / "recording.parts"
            write_part(directory)
            result = validate_target(directory, runner=unavailable)

        self.assertFalse(result.passed)
        self.assertIn("ffprobe_unavailable", [finding.code for finding in result.findings])

    def test_validation_does_not_modify_the_session_manifest(self) -> None:
        with TemporaryDirectory() as temporary:
            directory = Path(temporary) / "recording.parts"
            write_part(directory)
            values = manifest_values(
                directory, Path(temporary) / "missing.mp4", status="interrupted",
                finalization={"status": "not_started", "error": None},
            )
            path = directory / "session.json"
            original = (json.dumps(values, indent=2) + "\n").encode()
            path.write_bytes(original)

            validate_target(directory, runner=ProbeRunner())

            self.assertEqual(path.read_bytes(), original)

    def test_completed_session_with_pending_finalization_is_inconsistent(self) -> None:
        with TemporaryDirectory() as temporary:
            directory = Path(temporary) / "recording.parts"
            write_part(directory)
            values = manifest_values(
                directory, Path(temporary) / "missing.mp4",
                finalization={"status": "pending", "error": None},
            )
            (directory / "session.json").write_text(json.dumps(values), encoding="utf-8")
            result = validate_target(directory, runner=ProbeRunner())

        self.assertFalse(result.passed)
        self.assertIn("manifest_state_inconsistent", [
            finding.code for finding in result.findings
        ])


if __name__ == "__main__":
    unittest.main()
