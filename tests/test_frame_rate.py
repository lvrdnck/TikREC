from __future__ import annotations

import json
import subprocess
from fractions import Fraction
from pathlib import Path
import unittest

from tikrec.frame_rate import inspect_frame_rate, nominal_frame_rate
from tikrec.finalize import _build_ffmpeg_command


class FrameRateTests(unittest.TestCase):
    def test_prefers_average_over_timestamp_grid_estimate(self) -> None:
        commands = []

        def runner(command, **kwargs):
            commands.append((command, kwargs))
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps({
                "streams": [{"avg_frame_rate": "30000/1001", "r_frame_rate": "1000/1"}],
            }))

        self.assertEqual(inspect_frame_rate(Path("part.flv"), runner=runner), Fraction(30000, 1001))
        self.assertIn("v:0", commands[0][0])
        self.assertEqual(commands[0][1]["timeout"], 30)

    def test_falls_back_to_stream_rate_for_unavailable_average(self) -> None:
        for average in (None, "0/0", "N/A", "-15/1", "nan", "2147483648/1"):
            with self.subTest(average=average):
                def runner(command, **kwargs):
                    return subprocess.CompletedProcess(command, 0, stdout=json.dumps({
                        "streams": [{"avg_frame_rate": average, "r_frame_rate": "25/1"}],
                    }))
                self.assertEqual(inspect_frame_rate(Path("part.flv"), runner=runner), Fraction(25))

    def test_unusable_probe_results_fail_without_guessing(self) -> None:
        for output in ("not json", "{}", "[]", '{"streams": [null]}',
                       '{"streams": [{"avg_frame_rate": "0/0", "r_frame_rate": "0/0"}]}'):
            with self.subTest(output=output):
                def runner(command, **kwargs):
                    return subprocess.CompletedProcess(command, 0, stdout=output)
                with self.assertRaisesRegex(ValueError, "part.flv"):
                    inspect_frame_rate(Path("part.flv"), runner=runner)

    def test_probe_failures_include_part_context(self) -> None:
        for error in (FileNotFoundError("ffprobe"), subprocess.TimeoutExpired("ffprobe", 30)):
            with self.subTest(error=error):
                def runner(*args, **kwargs):
                    raise error
                with self.assertRaisesRegex(ValueError, "part.flv"):
                    inspect_frame_rate(Path("part.flv"), runner=runner)

    def test_nonzero_probe_exit_is_rejected(self) -> None:
        def runner(command, **kwargs):
            return subprocess.CompletedProcess(command, 1, stderr="invalid media")
        with self.assertRaisesRegex(ValueError, "invalid media"):
            inspect_frame_rate(Path("part.flv"), runner=runner)

    def test_mixed_rates_choose_maximum_without_duration_weighting(self) -> None:
        parts = (Path("slow.flv"), Path("fast.flv"))
        rates = {parts[0]: Fraction(15), parts[1]: Fraction(30000, 1001)}
        self.assertEqual(nominal_frame_rate(parts, inspector=rates.__getitem__), Fraction(30000, 1001))

    def test_identical_rates_remain_exact(self) -> None:
        self.assertEqual(nominal_frame_rate([Path("a"), Path("b")],
                                          inspector=lambda _: Fraction(24000, 1001)), Fraction(24000, 1001))

    def test_invalid_injected_rates_and_empty_parts_fail(self) -> None:
        for rates in ([], [Fraction(0)], [Fraction(-1)], [None]):
            with self.subTest(rates=rates):
                with self.assertRaises(ValueError):
                    nominal_frame_rate([Path(str(i)) for i in range(len(rates))],
                                       inspector=lambda part: rates[int(str(part))])

    def test_encoder_rate_does_not_force_cfr_or_a_level(self) -> None:
        command = _build_ffmpeg_command(
            (Path("a.flv"), Path("b.flv")), Path("output.mp4"),
            ffmpeg="ffmpeg", manifest=None, target_size=(720, 1280),
            nominal_rate=Fraction(30000, 1001),
        )
        self.assertEqual(command[command.index("-x264-params") + 1], "fps=30000/1001")
        self.assertEqual(command[command.index("-fps_mode:v") + 1], "passthrough")
        self.assertEqual(command[command.index("-enc_time_base:v") + 1], "filter")
        self.assertNotIn("-r", command)
        self.assertNotIn("-level:v", command)
        self.assertNotIn("fps=", command[command.index("-filter_complex") + 1])


if __name__ == "__main__":
    unittest.main()
