"""Characterize the synchronous boundary before extracting shared media planning."""

import inspect
import subprocess
from fractions import Fraction
from unittest.mock import patch

import pytest

from tests.test_finalize import _Runner, write_part
from tikrec.finalize import FinalizationError, finalize_parts
from tikrec.frame_rate import inspect_frame_rate


def test_public_signature_and_injected_copy_contract(tmp_path):
    signature = inspect.signature(finalize_parts)
    assert list(signature.parameters) == [
        "parts", "output_path", "ffmpeg", "runner", "progress",
        "frame_rate_inspector", "on_input_decode",
    ]
    assert signature.parameters["runner"].default is subprocess.run
    assert signature.parameters["frame_rate_inspector"].default is inspect_frame_rate
    first, second = tmp_path / "part-9999.flv", tmp_path / "part-10000.flv"
    for part in (first, second):
        write_part(part, b"same")
    runner, health = _Runner(read_manifest=True), []
    output = tmp_path / "final.mp4"
    assert finalize_parts([second, first], output, runner=runner,
                          on_input_decode=health.append) == output
    command = runner.commands[0]
    assert command[:3] == ["ffmpeg", "-nostdin", "-n"]
    assert command[3:8] == ["-f", "concat", "-safe", "0", "-i"]
    assert command[9:] == ["-map", "0", "-c", "copy", "-movflags", "+faststart",
                           str(tmp_path / ".final.partial.mp4")]
    assert runner.manifest.index(str(first)) < runner.manifest.index(str(second))
    assert health[0]["status"] == "not_checked"
    assert not list(tmp_path.glob("*.ffconcat"))


def test_reencode_settings_timing_and_degraded_tail_contract(tmp_path):
    parts = [tmp_path / "part-0001.flv", tmp_path / "part-0002.flv"]
    for part, config in zip(parts, (b"a", b"b")):
        write_part(part, config)
    stderr = "benign\n" * 4000 + "[h264 @ 0x1] error while decoding MB 1 2"
    runner, health = _Runner(stderr=stderr), []
    with patch("tikrec.finalize.avc_configuration_dimensions", side_effect=[(64, 80), (80, 64)]):
        finalize_parts(parts[::-1], tmp_path / "final.mp4", runner=runner,
                       frame_rate_inspector=lambda part: Fraction(15 if part == parts[0] else 25),
                       on_input_decode=health.append)
    command = runner.commands[0]
    assert command[3:7] == ["-i", str(parts[0]), "-i", str(parts[1])]
    graph = command[command.index("-filter_complex") + 1]
    assert "scale=80:80:force_original_aspect_ratio=decrease" in graph
    assert "pad=80:80:(ow-iw)/2:(oh-ih)/2,setsar=1,setpts=PTS-STARTPTS" in graph
    assert "asetpts=PTS-STARTPTS" in graph and "concat=n=2:v=1:a=1" in graph
    assert command[command.index("-c:v"):] == [
        "-c:v", "libx264", "-c:a", "aac", "-movflags", "+faststart",
        "-x264-params", "fps=25/1", "-fps_mode:v", "passthrough",
        "-enc_time_base:v", "filter", str(tmp_path / ".final.partial.mp4"),
    ]
    assert health[0]["status"] == "degraded"
    assert health[0]["diagnostic_codes"] == ["h264_macroblock"]


def test_public_failure_deletes_partial_and_manifest_preserves_sources(tmp_path):
    part = tmp_path / "part-0001.flv"
    write_part(part, b"same")
    before = part.read_bytes()
    with pytest.raises(FinalizationError):
        finalize_parts([part], tmp_path / "final.mp4", runner=_Runner(returncode=9))
    assert part.read_bytes() == before
    assert sorted(path.name for path in tmp_path.iterdir()) == [part.name]
