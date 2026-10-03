"""Focused checks for the disposable #52 harness; never use production processes."""

import json
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace

import pytest

from tests.diagnostics.issue52_priority import bounded_runner, percentile, stop_owned
from tests.diagnostics.priority_load import run_load
from tests.diagnostics.priority_windows import Metrics


def test_percentiles_are_interpolated_and_empty_is_unavailable():
    assert percentile([], .95) is None
    assert percentile([5], .95) == 5
    assert percentile([10, 0], .95) == 9.5
    assert percentile([1, 2, 3], .5) == 2


def test_probe_has_fixed_work_monotonic_times_and_honors_stop(tmp_path):
    stop, output = tmp_path / "stop", tmp_path / "probe.json"
    run_load("probe", stop, output, .06)
    records = json.loads(output.read_text())
    assert len(records) >= 2
    assert len({r["check"] for r in records}) == 1
    assert all(r["scheduled"] <= r["wake"] <= r["end"] for r in records)
    stop.touch()
    run_load("probe", stop, output, .06)
    assert json.loads(output.read_text()) == []


def test_validator_deadline_is_bounded_without_media_command_changes(monkeypatch):
    calls = []
    monkeypatch.setattr(subprocess, "run", lambda command, **kw: calls.append((command, kw)))
    command = ["ffprobe", "-show_frames", "synthetic.flv"]
    bounded_runner(command, timeout=90)
    bounded_runner(command, timeout=2)
    assert calls == [(command, {"timeout": 30}), (command, {"timeout": 2})]


def test_stop_does_not_touch_a_completed_popen():
    done = SimpleNamespace(poll=lambda: 0, terminate=lambda: pytest.fail("unowned stop"))
    stop_owned(done)


def test_stop_escalates_only_the_owned_child_after_timeout():
    calls = []

    def wait(timeout):
        calls.append(("wait", timeout))
        if len(calls) == 2:
            raise subprocess.TimeoutExpired("owned fixture", timeout)

    child = SimpleNamespace(poll=lambda: None, wait=wait,
                            terminate=lambda: calls.append("terminate"),
                            kill=lambda: calls.append("kill"))
    stop_owned(child)
    assert calls == ["terminate", ("wait", 5), "kill", ("wait", 5)]


@pytest.mark.skipif(sys.platform != "win32", reason="native Windows child metrics")
@pytest.mark.parametrize("priority", [0x20, 0x4000])
def test_metrics_observe_only_the_explicitly_created_child(priority):
    if shutil.which("ffmpeg") is None:
        pytest.skip("native metrics smoke check requires existing FFmpeg")
    # Native priority smoke checks also target only disposable FFmpeg children.
    child = subprocess.Popen([
        "ffmpeg", "-nostdin", "-re", "-f", "lavfi", "-i", "sine=sample_rate=44100",
        "-t", "2", "-f", "s16le", "-"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=priority)
    try:
        value = Metrics(child).sample()
        assert value["priority_class"] == priority
        assert value["physical_available"] > 0
        assert value["cpu_seconds"] >= 0
        assert value["read_bytes"] >= 0 and value["write_bytes"] >= 0
    finally:
        stop_owned(child)


def test_harness_refuses_the_production_recording_root():
    result = subprocess.run([sys.executable, "-m", "tests.diagnostics.issue52_priority",
                             "prepare", "--root", str(Path.home() / "Videos")],
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == 2
    assert "external TikREC-tests" in result.stderr
