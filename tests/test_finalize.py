from __future__ import annotations

import os
import subprocess
from fractions import Fraction
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

from tikrec.flv import FlvTag
from tikrec.finalize import FinalizationError, _run_ffmpeg, finalize_parts


def write_part(path: Path, configuration: bytes) -> None:
    header = b"FLV\x01\x05\x00\x00\x00\x09\x00\x00\x00\x00"
    tag = FlvTag(9, 0, b"\x00\x00\x00", b"\x17\x00\x00\x00\x00" + configuration)
    path.write_bytes(header + tag.encoded())


class FinalizeTests(unittest.TestCase):
    def test_rejects_no_parts_before_starting_ffmpeg(self) -> None:
        with TemporaryDirectory() as directory:
            runner = _Runner()

            with self.assertRaisesRegex(ValueError, "at least one"):
                finalize_parts([], Path(directory) / "final.mp4", runner=runner)

            self.assertEqual(runner.commands, [])

    def test_rejects_missing_part_before_starting_ffmpeg(self) -> None:
        with TemporaryDirectory() as directory:
            runner = _Runner()

            with self.assertRaisesRegex(FileNotFoundError, "missing"):
                finalize_parts([Path(directory) / "part-0001.flv"], Path(directory) / "final.mp4", runner=runner)

            self.assertEqual(runner.commands, [])

    def test_one_part_remuxes_without_reencoding(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            part = root / "part-0001.flv"
            write_part(part, b"same")
            runner = _Runner()

            output = finalize_parts([part], root / "final.mp4", ffmpeg="fake-ffmpeg", runner=runner)

            self.assertEqual(output, root / "final.mp4")
            self.assertTrue(output.is_file())
            self.assertEqual(runner.commands[0][0], "fake-ffmpeg")
            self.assertIn("-c", runner.commands[0])
            self.assertIn("copy", runner.commands[0])
            self.assertTrue(part.exists())

    def test_multiple_parts_are_sorted_in_the_concat_manifest(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            first = root / "part-0001.flv"
            second = root / "part-0002.flv"
            write_part(first, b"same")
            write_part(second, b"same")
            runner = _Runner(read_manifest=True)

            finalize_parts([second, first], root / "final.mp4", runner=runner)

            self.assertLess(runner.manifest.index(str(first.resolve())), runner.manifest.index(str(second.resolve())))

    def test_changed_configurations_use_a_timestamp_resetting_filter_graph(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            first = root / "part-0001.flv"
            second = root / "part-0002.flv"
            write_part(first, b"first")
            write_part(second, b"second")
            runner = _Runner()
            progress: list[str] = []

            with patch("tikrec.finalize.avc_configuration_dimensions", return_value=(720, 1280)):
                finalize_parts(
                    [first, second], root / "final.mp4",
                    runner=runner, progress=progress.append,
                    frame_rate_inspector=lambda part: Fraction(15 if part == first else 25),
                )

            command = runner.commands[0]
            graph = command[command.index("-filter_complex") + 1]
            self.assertIn("setpts=PTS-STARTPTS", graph)
            self.assertIn("asetpts=PTS-STARTPTS", graph)
            self.assertIn("concat=n=2:v=1:a=1", graph)
            self.assertEqual(command[command.index("-c:v") + 1], "libx264")
            self.assertEqual(command[command.index("-x264-params") + 1], "fps=25/1")
            self.assertIn(
                "finalization started: re-encoding 2 part(s); "
                "this may take several minutes or longer",
                progress,
            )

    def test_failed_ffmpeg_includes_stderr_and_deletes_partial_output(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            part = root / "part-0001.flv"
            write_part(part, b"same")
            runner = _Runner(returncode=9, stderr="decoder exploded", writes_output=True)

            with self.assertRaisesRegex(FinalizationError, "decoder exploded") as error:
                finalize_parts([part], root / "final.mp4", runner=runner)

            self.assertIn("code 9", str(error.exception))
            self.assertFalse((root / "final.mp4").exists())
            self.assertFalse((root / ".final.partial.mp4").exists())

    def test_reports_ffmpeg_stderr_and_preserves_it_on_failure(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            part = root / "part-0001.flv"
            write_part(part, b"same")
            progress: list[str] = []
            runner = _Runner(returncode=9, stderr="out_time=00:00:01.000000\ndecoder exploded")

            with self.assertRaisesRegex(FinalizationError, "decoder exploded"):
                finalize_parts(
                    [part], root / "final.mp4", runner=runner, progress=progress.append,
                )

        self.assertEqual(progress, [
            "finalization started: stream-copying 1 part(s)",
            "encoding progress: 00:00:01.000000",
            "ffmpeg: decoder exploded",
        ])

    def test_default_runner_streams_ffmpeg_stderr_and_retains_diagnostics(self) -> None:
        progress: list[str] = []
        process = _Process("out_time=00:00:01.000000\ndecoder exploded\n", 9)

        with patch("tikrec.finalize.subprocess.Popen", return_value=process) as popen:
            result = _run_ffmpeg(["ffmpeg", "-n"], subprocess.run, progress.append)

        self.assertEqual(result.returncode, 9)
        self.assertEqual(result.stderr, "out_time=00:00:01.000000\ndecoder exploded\n")
        self.assertEqual(progress, [
            "encoding progress: 00:00:01.000000",
            "ffmpeg: decoder exploded",
        ])
        self.assertEqual(popen.call_args.args[0], [
            "ffmpeg", "-n", "-progress", "pipe:2", "-nostats",
            "-loglevel", "warning",
        ])

    def test_repeated_late_sei_diagnostics_are_reported_once(self) -> None:
        message = (
            "[h264 @ 0x1] Late SEI is not implemented. Update FFmpeg.\n"
            "[h264 @ 0x1] If you want to help, upload a sample.\n"
            "[h264 @ 0x2] Late SEI is not implemented. Update FFmpeg.\n"
            "out_time=00:00:02.000000\n"
        )
        progress: list[str] = []
        process = _Process(message, 0)

        with patch("tikrec.finalize.subprocess.Popen", return_value=process):
            result = _run_ffmpeg(["ffmpeg", "-n"], subprocess.run, progress.append)

        self.assertEqual(result.stderr, message)
        self.assertEqual(progress, [
            "ffmpeg: late H.264 SEI metadata is unsupported; repeated warnings suppressed",
            "encoding progress: 00:00:02.000000",
        ])

    def test_interrupting_ffmpeg_progress_terminates_and_reaps_ffmpeg(self) -> None:
        process = _Process("out_time=00:00:01.000000\n", 0)

        with patch("tikrec.finalize.subprocess.Popen", return_value=process):
            with self.assertRaises(KeyboardInterrupt):
                _run_ffmpeg(
                    ["ffmpeg", "-n"],
                    subprocess.run,
                    lambda _: (_ for _ in ()).throw(KeyboardInterrupt),
                )

        self.assertTrue(process.terminated)
        self.assertEqual(process.wait_calls, 1)

    def test_success_promotes_partial_output_atomically(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            part = root / "part-0001.flv"
            output = root / "final.mp4"
            write_part(part, b"same")
            runner = _Runner()

            with patch("tikrec.finalize.os.replace", wraps=os.replace) as replace:
                finalize_parts([part], output, runner=runner)

            replace.assert_called_once_with(root / ".final.partial.mp4", output)
            self.assertEqual(output.read_bytes(), b"finished media")
            self.assertFalse((root / ".final.partial.mp4").exists())

    def test_temporary_mp4_output_retains_the_container_suffix(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            part = root / "part-0001.flv"
            write_part(part, b"same")
            runner = _Runner()

            finalize_parts([part], root / "final.mp4", runner=runner)

            self.assertEqual(Path(runner.commands[0][-1]).name, ".final.partial.mp4")
            self.assertEqual(Path(runner.commands[0][-1]).suffix, ".mp4")

    def test_temporary_output_preserves_non_mp4_container_suffix(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            part = root / "part-0001.flv"
            write_part(part, b"same")
            runner = _Runner()

            finalize_parts([part], root / "final.mkv", runner=runner)

            self.assertEqual(Path(runner.commands[0][-1]).name, ".final.partial.mkv")
            self.assertEqual(Path(runner.commands[0][-1]).suffix, ".mkv")

    def test_rejects_an_existing_destination_without_running_ffmpeg(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            part = root / "part-0001.flv"
            output = root / "final.mp4"
            write_part(part, b"same")
            output.write_bytes(b"keep")
            runner = _Runner()

            with self.assertRaisesRegex(FileExistsError, "refusing to overwrite"):
                finalize_parts([part], output, runner=runner)

            self.assertEqual(output.read_bytes(), b"keep")
            self.assertEqual(runner.commands, [])

    def test_paths_with_spaces_are_passed_as_separate_arguments(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory) / "parts with spaces"
            root.mkdir()
            part = root / "part one.flv"
            output = root / "final media.mp4"
            write_part(part, b"same")
            runner = _Runner(read_manifest=True)

            finalize_parts([part], output, ffmpeg="fake ffmpeg", runner=runner)

            self.assertEqual(runner.commands[0][0], "fake ffmpeg")
            self.assertIn(str(output.with_name(".final media.partial.mp4")), runner.commands[0])
            self.assertIn(str(part.resolve()), runner.manifest)


class _Runner:
    def __init__(
        self,
        *,
        returncode: int = 0,
        stderr: str = "",
        writes_output: bool = True,
        read_manifest: bool = False,
    ) -> None:
        self.returncode = returncode
        self.stderr = stderr
        self.writes_output = writes_output
        self.read_manifest = read_manifest
        self.commands: list[list[str]] = []
        self.manifest = ""

    def __call__(self, command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        self.commands.append(command)
        if self.read_manifest:
            self.manifest = Path(command[command.index("-i") + 1]).read_text()
        if self.writes_output:
            Path(command[-1]).write_bytes(b"finished media")
        return subprocess.CompletedProcess(command, self.returncode, stderr=self.stderr)


class _Process:
    def __init__(self, stderr: str, returncode: int) -> None:
        self.stderr = StringIO(stderr)
        self.returncode = returncode
        self.terminated = False
        self.wait_calls = 0

    def wait(self) -> int:
        self.wait_calls += 1
        return self.returncode

    def terminate(self) -> None:
        self.terminated = True
        self.returncode = -15


if __name__ == "__main__":
    unittest.main()
