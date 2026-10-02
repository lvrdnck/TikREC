"""Startup-selected automatic raw-copy never overrides accepted recovery intent."""

from threading import Event
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from tikrec.automation_state import AutomationStateStore
from tikrec.capture import CaptureResult
from tikrec.recording import RecordingController
from tikrec.recording_manager import RecordingManager
from tikrec.service import RecordingHTTPServer, serve
from tikrec.tiktok_identity import LiveResolution
from tests.test_automation import _cycle
from tests.test_reconciliation import reconciler, saved_session


@pytest.mark.parametrize("accepted", [False, True])
def test_startup_and_recovery_preserve_accepted_raw_flag_despite_opposite_policy(tmp_path, accepted):
    store, job, _ = saved_session(tmp_path, raw_copy_enabled=accepted)
    entered = Event()
    calls = []

    def resume(page, **options):
        calls.append(options)
        assert options["session_id"] == job.session_id
        assert store.load().raw_copy_enabled is accepted
        options["state"]("recording")
        entered.set()
        assert options["stop_event"].wait(5)
        return CaptureResult((), None, True, resumed=True)

    worker = RecordingController(store=store, reconciler=reconciler(
        store, resolver=lambda _: LiveResolution("123", "https://cdn.test/offline.flv"),
        resume_capture=resume))
    manager = RecordingManager((worker,))
    monitor = SimpleNamespace(start=lambda: None, stop=lambda: None, join=lambda: None)
    policy = () if accepted else ("creator",)
    with patch("tikrec.service.ThreadingHTTPServer.__init__", return_value=None):
        server = RecordingHTTPServer(manager=manager, monitor=monitor,
            automatic_raw_copy_creators=policy,
            automation_store=AutomationStateStore(tmp_path / "automation.json"))
    try:
        assert entered.wait(2), (worker.status().get("error"), worker.status().get("recovery_reason"))
        assert ("raw_copy_dir" in calls[0]) is accepted
        if accepted:
            assert str(calls[0]["raw_copy_dir"]) == job.parts_directory
        server.automation.cycle_completed(_cycle(1, ("creator", "live", "123")))
        assert manager.status()["session_id"] == job.session_id
        assert manager.status()["raw_copy_enabled"] is accepted
        assert manager.status()["resume_count"] == 1
        assert not manager.status()["stop_requested"]
        assert len(calls) == 1
    finally:
        server.shutdown_components()


def test_serve_forwards_startup_opt_in_without_monitor_policy_reload():
    server = SimpleNamespace(serve_forever=lambda: (_ for _ in ()).throw(KeyboardInterrupt()),
                             shutdown_components=lambda: None)
    with patch("tikrec.service.RecordingHTTPServer") as factory:
        factory.return_value.__enter__.return_value = server
        serve(automatic_raw_copy_creators=("alpha",))
    assert factory.call_args.kwargs["automatic_raw_copy_creators"] == ("alpha",)
