from __future__ import annotations

import json
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

from scripts.validate_parts import validate_parts


class ValidatePartsTests(unittest.TestCase):
    @staticmethod
    def successful_runner(command, **_: object):
        if "-show_packets" in command:
            packets = {
                "packets": [
                    {"stream_index": 0, "dts": 0},
                    {"stream_index": 1, "dts": 0},
                    {"stream_index": 0, "dts": 40},
                    {"stream_index": 1, "dts": 21},
                ]
            }
            return SimpleNamespace(returncode=0, stdout=json.dumps(packets), stderr="")
        return SimpleNamespace(returncode=0, stderr="")

    def test_reports_each_clean_part_after_both_checks(self) -> None:
        calls: list[list[str]] = []

        def runner(command, **_: object):
            calls.append(command)
            return self.successful_runner(command)

        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "part-0002.flv").write_bytes(b"")
            (root / "part-0001.flv").write_bytes(b"")
            stdout = StringIO()
            code = validate_parts(root, runner=runner, stdout=stdout, stderr=StringIO())

        self.assertEqual(code, 0)
        self.assertEqual(len(calls), 4)
        self.assertEqual([command[-1] for command in calls], [
            str(root / "part-0001.flv"),
            str(root / "part-0001.flv"),
            str(root / "part-0002.flv"),
            str(root / "part-0002.flv"),
        ])
        self.assertEqual(stdout.getvalue().splitlines(), [
            "PASS part-0001.flv", "PASS part-0002.flv", "2/2 parts passed",
        ])

    def test_reports_decoder_error_as_a_failed_decode_check(self) -> None:
        def runner(command, **_: object):
            if "-show_frames" in command and command[-1].endswith("part-0002.flv"):
                return SimpleNamespace(returncode=0, stderr="AAC decode error")
            return self.successful_runner(command)

        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "part-0001.flv").write_bytes(b"")
            (root / "part-0002.flv").write_bytes(b"")
            stdout = StringIO()
            stderr = StringIO()
            code = validate_parts(root, runner=runner, stdout=stdout, stderr=stderr)

        self.assertEqual(code, 1)
        self.assertIn("PASS part-0001.flv", stdout.getvalue())
        self.assertIn("FAIL part-0002.flv", stdout.getvalue())
        self.assertIn("part-0002.flv decode check failed: AAC decode error", stderr.getvalue())

    def test_reports_duplicate_stored_dts_as_a_failed_dts_check(self) -> None:
        def runner(command, **_: object):
            if "-show_packets" in command:
                packets = {
                    "packets": [
                        {"stream_index": 0, "dts": 100},
                        {"stream_index": 0, "dts": 100},
                    ]
                }
                return SimpleNamespace(
                    returncode=0, stdout=json.dumps(packets), stderr=""
                )
            return self.successful_runner(command)

        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "part-0001.flv").write_bytes(b"")
            stdout = StringIO()
            stderr = StringIO()
            code = validate_parts(root, runner=runner, stdout=stdout, stderr=stderr)

        self.assertEqual(code, 1)
        self.assertIn("FAIL part-0001.flv", stdout.getvalue())
        self.assertIn("part-0001.flv DTS check failed", stderr.getvalue())
        self.assertIn("stream 0 DTS 100 is not strictly greater than 100", stderr.getvalue())

    def test_prints_available_per_part_timing_metadata(self) -> None:
        record = {
            "connection": 1,
            "outcome": "closed",
            "part_timings": [{
                "name": "part-0001.flv",
                "configuration_timestamp": 0,
                "first_media_timestamp": 3_427_480,
                "first_keyframe_timestamp": 3_427_493,
                "keyframe_gate_duration": 13,
                "last_tag_timestamp": 3_430_000,
            }],
        }

        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "part-0001.flv").write_bytes(b"")
            (root / "connections.jsonl").write_text(json.dumps(record) + "\n")
            stdout = StringIO()
            validate_parts(
                root,
                runner=self.successful_runner,
                stdout=stdout,
                stderr=StringIO(),
            )

        self.assertIn("Timing summary:", stdout.getvalue())
        self.assertIn("gate=13ms", stdout.getvalue())
        self.assertIn("first-media=3427480", stdout.getvalue())

    def test_rejects_a_directory_without_retained_parts(self) -> None:
        with TemporaryDirectory() as directory:
            stderr = StringIO()
            code = validate_parts(Path(directory), stdout=StringIO(), stderr=stderr)

        self.assertEqual(code, 2)
        self.assertIn("no retained FLV parts", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
