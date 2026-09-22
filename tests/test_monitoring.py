"""Offline tests for read-only creator monitoring and sanitized snapshots."""

import json
from threading import Event

from tikrec.capture import CaptureResult
from tikrec.monitoring import CreatorMonitor, POLL_INTERVAL_SECONDS
from tikrec.recording import RecordingController
from tikrec.tiktok import (TikTokOfflineError, TikTokResolutionError,
                           TikTokResolutionTransientError)
from tikrec.tiktok_identity import LiveResolution


def test_empty_creator_list_starts_no_polling_work():
    monitor = CreatorMonitor((), resolver=lambda _: (_ for _ in ()).throw(AssertionError()))
    monitor.start()
    assert monitor.snapshot() == {
        "poll_interval_seconds": 30.0,
        "running": False,
        "cycle_in_progress": False,
        "cycle_count": 0,
        "last_cycle_started_at": None,
        "last_cycle_completed_at": None,
        "creators": [],
    }
    monitor.shutdown()


def test_immediate_cycles_are_sequential_ordered_and_wait_after_completion():
    events = []
    finished = Event()

    def resolver(page):
        events.append("resolve:" + page.split("@", 1)[1].split("/", 1)[0])
        return LiveResolution("123", "https://cdn.test/live.flv?secret=discard")

    def waiter(seconds):
        events.append(f"wait:{seconds}")
        if events.count("wait:30.0") == 2:
            finished.set()
            return True
        return False

    monitor = CreatorMonitor(("first", "second"), resolver=resolver, waiter=waiter)
    monitor.start()
    assert finished.wait(2)
    monitor.join()
    assert events == [
        "resolve:first", "resolve:second", "wait:30.0",
        "resolve:first", "resolve:second", "wait:30.0",
    ]
    snapshot = monitor.snapshot()
    assert snapshot["cycle_count"] == 2
    assert snapshot["last_cycle_completed_at"] >= snapshot["last_cycle_started_at"]
    assert POLL_INTERVAL_SECONDS == 30.0


def test_live_offline_and_failures_use_conservative_fixed_categories():
    signed = "https://cdn.test/live.flv?token=must-not-escape"
    outcomes = {
        "live": LiveResolution("000789", signed),
        "offline": TikTokOfflineError("not live", 4, "789"),
        "transient": TikTokResolutionTransientError("secret URL", kind="network"),
        "restricted": TikTokResolutionError("anonymous access restricted: secret"),
        "malformed": "not structured identity",
        "broken": RuntimeError("secret unexpected response"),
    }
    calls = []
    finished = Event()

    def resolver(page):
        creator = page.split("@", 1)[1].split("/", 1)[0]
        calls.append(creator)
        result = outcomes[creator]
        if isinstance(result, Exception):
            raise result
        return result

    def waiter(_):
        finished.set()
        return True

    creators = tuple(outcomes)
    monitor = CreatorMonitor(creators, resolver=resolver, waiter=waiter, clock=lambda: 12.5)
    monitor.start()
    assert finished.wait(2)
    monitor.join()
    snapshot = monitor.snapshot()
    observations = {item["creator"]: item for item in snapshot["creators"]}
    assert calls == list(creators)
    assert observations["live"] == {
        "creator": "live", "state": "live", "observed_at": 12.5,
        "room_id": "789", "unknown_reason": None,
    }
    assert observations["offline"]["state"] == "offline"
    assert observations["transient"]["unknown_reason"] == "transient"
    assert observations["restricted"]["unknown_reason"] == "unverifiable"
    assert observations["malformed"]["unknown_reason"] == "unverifiable"
    assert observations["broken"]["unknown_reason"] == "unexpected"
    assert all(
        item["state"] == "unknown"
        for name, item in observations.items()
        if name not in {"live", "offline"}
    )
    serialized = json.dumps(snapshot)
    assert "must-not-escape" not in serialized and "secret" not in serialized


def test_snapshot_is_thread_safe_while_resolver_is_in_flight():
    entered, release, completed = Event(), Event(), Event()

    def resolver(_):
        entered.set()
        assert release.wait(2)
        return LiveResolution("42", "https://cdn.test/live.flv?token=discard")

    def waiter(_):
        completed.set()
        return True

    monitor = CreatorMonitor(("creator",), resolver=resolver, waiter=waiter)
    monitor.start()
    assert entered.wait(2)
    for _ in range(100):
        snapshot = monitor.snapshot()
        assert snapshot["cycle_in_progress"]
        assert snapshot["creators"][0]["state"] == "pending"
    release.set()
    assert completed.wait(2)
    monitor.join()
    assert monitor.snapshot()["creators"][0]["state"] == "live"


def test_shutdown_wakes_interval_wait_and_joins_worker():
    observed = Event()

    def resolver(_):
        observed.set()
        return LiveResolution("42", "https://cdn.test/live.flv")

    monitor = CreatorMonitor(("creator",), resolver=resolver)
    monitor.start()
    assert observed.wait(2)
    monitor.shutdown()
    assert not monitor.snapshot()["running"]


def test_monitoring_does_not_interact_with_active_recording(tmp_path):
    recording_started, release_recording, monitor_done = Event(), Event(), Event()

    def capture(url, **kwargs):
        kwargs["state"]("recording")
        recording_started.set()
        assert release_recording.wait(2)
        return CaptureResult((), None)

    controller = RecordingController(capture=capture)
    controller.start(
        "https://www.tiktok.com/@manual/live", str(tmp_path / "manual.mp4")
    )
    assert recording_started.wait(2)
    before = controller.status()
    monitor = CreatorMonitor(
        ("observed",),
        resolver=lambda _: LiveResolution("99", "https://cdn.test/live.flv"),
        waiter=lambda _: monitor_done.set() or True,
    )
    try:
        monitor.start()
        assert monitor_done.wait(2)
        monitor.join()
        after = controller.status()
        assert before["session_id"] == after["session_id"]
        assert after["state"] == "recording" and not after["stop_requested"]
    finally:
        monitor.shutdown()
        release_recording.set()
        controller.shutdown()
