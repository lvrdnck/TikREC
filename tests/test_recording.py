"""Offline tests for single-job ownership and safe status."""

import json
from threading import Event, Thread
from unittest.mock import patch

import pytest

from tikrec.capture import CaptureError, CaptureResult
from tikrec.recording import RecordingBusy, RecordingController, normalize_live_url


PAGE = "https://www.tiktok.com/@creator/live"


def test_idle_and_health():
    controller = RecordingController()
    assert controller.status() == {"state": "idle", "active": False}
    assert controller.health()["available"]
    assert controller.ownership() == {
        "current": False, "session_id": None, "source_url": None, "room_id": None,
        "output_path": None, "parts_directory": None,
    }


def test_narrow_ownership_tracks_proven_room_without_progress(tmp_path):
    entered = Event()
    def capture(url, **kwargs):
        entered.set()
        assert kwargs["stop_event"].wait(2)
        return CaptureResult((), None, True)
    controller = RecordingController(capture=capture)
    first = controller.start("https://www.tiktok.com/@Alpha/live",
                             str(tmp_path / "first.mp4"))
    assert entered.wait(2)
    try:
        assert controller.ownership() == {
            "current": True, "session_id": first["session_id"],
            "source_url": "https://www.tiktok.com/@Alpha/live", "room_id": None,
            "output_path": str(tmp_path / "first.mp4"),
            "parts_directory": str(tmp_path / "first.parts"),
        }
        controller._identity("123")
        assert controller.ownership()["room_id"] == "123"
    finally:
        controller.shutdown()
    assert controller.ownership()["current"] is False


def test_start_status_stop_and_completed_output(tmp_path):
    entered = Event()
    finalizing = Event()
    release = Event()
    received = []

    def capture(url, **kwargs):
        received.append(kwargs)
        kwargs["state"]("resolving")
        kwargs["state"]("recording")
        parts = kwargs["parts_directory"]
        parts.mkdir()
        part = parts / "part-0001.flv"
        part.write_bytes(b"retained")
        kwargs["heartbeat"](part, 8)
        entered.set()
        assert kwargs["stop_event"].wait(2)
        kwargs["state"]("finalizing")
        finalizing.set()
        assert release.wait(2)
        kwargs["output_path"].write_bytes(b"output")
        return CaptureResult((part,), kwargs["output_path"], True)

    controller = RecordingController(capture=capture)
    output = str(tmp_path / "out.mp4")
    initial = controller.start(PAGE + "?token=discard", output)
    try:
        assert initial["state"] == "resolving"
        assert entered.wait(2)
        assert not controller.health()["available"]
        status = controller.status()
        assert status["state"] == "recording"
        assert status["part_count"] == 1 and status["bytes_written"] == 8
        assert status["source_url"] == PAGE
        with pytest.raises(RecordingBusy):
            controller.start(PAGE, str(tmp_path / "second.mp4"))
        assert controller.stop()["stop_requested"]
        assert finalizing.wait(2)
        assert controller.status()["state"] == "finalizing"
        assert controller.stop()["active"]
        with pytest.raises(RecordingBusy):
            controller.start(PAGE, str(tmp_path / "second.mp4"))
    finally:
        release.set()
        controller.shutdown()
    result = controller.status()
    assert result["state"] == "completed" and result["interrupted"]
    assert result["final_output_path"] == output and not result["active"]
    assert received[0]["session_id"] == result["session_id"]
    assert (tmp_path / "out.parts/part-0001.flv").read_bytes() == b"retained"


def test_failed_capture_redacts_urls_and_retains_parts(tmp_path):
    def capture(url, **kwargs):
        parts = kwargs["parts_directory"]
        parts.mkdir()
        part = parts / "part-0001.flv"
        part.write_bytes(b"keep")
        raise CaptureError("read failed https://cdn.test/a.flv?token=secret", (part,))

    controller = RecordingController(capture=capture)
    controller.start(PAGE, str(tmp_path / "out.mp4"))
    controller.shutdown()
    status = controller.status()
    assert status["state"] == "failed" and status["part_count"] == 1
    assert "secret" not in json.dumps(status) and "[URL redacted]" in status["error"]
    assert (tmp_path / "out.parts/part-0001.flv").read_bytes() == b"keep"


@pytest.mark.parametrize("url", ["https://cdn.test/a.flv?secret=x", "https://evil.test/@x/live",
                                  "https://www.tiktok.com:999/@x/live",
                                  "https://me@www.tiktok.com/@x/live"])
def test_rejects_arbitrary_source_urls(url):
    with pytest.raises(ValueError):
        normalize_live_url(url)


def test_refuses_relative_output_and_existing_artifacts(tmp_path):
    controller = RecordingController()
    with pytest.raises(ValueError, match="absolute"):
        controller.start(PAGE, "out.mp4")
    output = tmp_path / "out.mp4"
    output.write_bytes(b"keep")
    with pytest.raises(ValueError, match="already exist"):
        controller.start(PAGE, str(output))
    assert output.read_bytes() == b"keep"


def test_raw_copy_opt_in_is_passed_only_to_the_selected_job(tmp_path):
    calls = []
    def capture(url, **kwargs):
        calls.append(kwargs)
        return CaptureResult((), None)
    controller = RecordingController(capture=capture)
    controller.start(PAGE, str(tmp_path / "raw.mp4"), raw_copy=True)
    controller._worker.join(2)
    controller.start(PAGE, str(tmp_path / "normal.mp4"))
    controller.shutdown()
    assert calls[0]["raw_copy_dir"] == tmp_path / "raw.parts"
    assert "raw_copy_dir" not in calls[1]


def test_raw_copy_option_requires_a_boolean(tmp_path):
    controller = RecordingController()
    with pytest.raises(ValueError, match="boolean"):
        controller.start(PAGE, str(tmp_path / "out.mp4"), raw_copy=1)


def test_shutdown_waits_for_worker_and_rejects_new_jobs(tmp_path):
    entered, finalizing, release, done = Event(), Event(), Event(), Event()

    def capture(url, **kwargs):
        entered.set()
        assert kwargs["stop_event"].wait(2)
        finalizing.set()
        assert release.wait(2)
        return CaptureResult((), None, True)

    controller = RecordingController(capture=capture)
    controller.start(PAGE, str(tmp_path / "out.mp4"))
    assert entered.wait(2)

    def shutdown():
        controller.shutdown()
        done.set()

    thread = Thread(target=shutdown)
    thread.start()
    try:
        assert finalizing.wait(2) and not done.is_set()
        with pytest.raises(RecordingBusy):
            controller.start(PAGE, str(tmp_path / "second.mp4"))
    finally:
        release.set()
        thread.join(2)
    assert done.is_set()


def test_another_job_can_start_after_completion(tmp_path):
    first_done = Event()

    def capture(url, **kwargs):
        first_done.set()
        return CaptureResult((), None, True)

    controller = RecordingController(capture=capture)
    first = controller.start(PAGE, str(tmp_path / "first.mp4"))
    assert first_done.wait(2)
    # Joining the worker is deterministic; shutdown would intentionally close the controller.
    controller._worker.join(2)
    second = controller.start(PAGE, str(tmp_path / "second.mp4"))
    controller.shutdown()
    assert first["session_id"] != second["session_id"]


def test_thread_start_failure_releases_slot_and_allows_shutdown(tmp_path):
    controller = RecordingController()
    with patch("tikrec.recording.Thread.start", side_effect=RuntimeError("cannot start")):
        with pytest.raises(RuntimeError, match="could not start"):
            controller.start(PAGE, str(tmp_path / "out.mp4"))
    assert controller.status()["state"] == "failed"
    assert not controller.status()["active"]
    controller.shutdown()
