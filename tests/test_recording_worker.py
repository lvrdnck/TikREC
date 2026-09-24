"""Service worker retains the root writer lease through active capture."""

from threading import Event

import pytest

from tikrec.capture import CaptureResult
from tikrec.lifecycle_lock import LifecycleBusy, acquire_lifecycle
from tikrec.recording import RecordingController


def test_active_worker_excludes_retention_until_capture_finishes(tmp_path):
    entered, release = Event(), Event()
    def capture(_url, **kwargs):
        entered.set()
        assert release.wait(3)
        return CaptureResult((), kwargs["output_path"])
    controller = RecordingController(capture=capture)
    controller.start("https://www.tiktok.com/@alpha/live", str(tmp_path / "out.mp4"))
    assert entered.wait(3)
    try:
        with pytest.raises(LifecycleBusy):
            acquire_lifecycle(tmp_path, "retention")
    finally:
        release.set()
        controller.shutdown()
    with acquire_lifecycle(tmp_path, "retention") as lease:
        lease.assert_held()
