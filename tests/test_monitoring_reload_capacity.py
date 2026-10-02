"""Reload preserves real durable workers and bounded automatic arbitration."""

from datetime import datetime
from types import SimpleNamespace

import pytest

from tikrec.admission import MINIMUM_FREE_BYTES, RecordingAdmission
from tikrec.automation import AutomationCoordinator
from tikrec.automation_state import AutomationStateStore
from tikrec.configuration import Configuration, ConfigurationStore
from tikrec.job_state import JobStateStore
from tikrec.monitoring import CreatorMonitor
from tikrec.tiktok import TikTokOfflineError
from tikrec.tiktok_identity import LiveResolution
from tests.test_automation_capacity import _components
from tests.test_recording_manager import CaptureHarness, _manager


@pytest.mark.parametrize("active_count", [1, 2])
def test_reload_removal_never_changes_active_workers_or_durable_jobs(tmp_path, monkeypatch, active_count):
    stores = (JobStateStore(tmp_path / "job.json"),
              JobStateStore(tmp_path / "job-2.json"))
    harness = CaptureHarness()
    manager = _manager(harness, stores=stores)
    for controller in manager.controllers:
        # Freeze derived elapsed status; compare every job field, not wall-clock drift.
        monkeypatch.setattr(controller, "_clock", lambda: 100.0)
    creators = ("alpha", "beta")[:active_count]
    for creator in creators:
        manager.start(f"https://www.tiktok.com/@{creator}/live",
                      str(tmp_path / f"{creator}.mp4"))
        harness.wait(creator)
    config = ConfigurationStore(tmp_path / "config.json")
    config.save(Configuration(monitored_creators=creators))
    admission = RecordingAdmission(
        tmp_path, manager.health, clock=lambda: datetime(2026, 10, 2),
        disk_usage=lambda _: SimpleNamespace(free=MINIMUM_FREE_BYTES),
    )
    coordinator = AutomationCoordinator(
        manager, admission, AutomationStateStore(tmp_path / "automation.json"),
    )
    def offline(_):
        raise TikTokOfflineError("not live", 4, "1")
    monitor = CreatorMonitor(
        creators, resolver=offline, cycle_completed=coordinator.cycle_completed,
        creator_loader=lambda: config.load(missing_ok=False).monitored_creators,
    )
    try:
        jobs_before = manager.jobs()
        bytes_before = [store.path.read_bytes() for store in stores if store.path.exists()]
        monitor._poll_cycle()
        config.save(Configuration(monitored_creators=("gamma",)))
        monitor._poll_cycle()
        config.path.write_text('{"private":"invalid"}', encoding="utf-8")
        monitor._poll_cycle()
        assert [item["creator"] for item in monitor.snapshot()["creators"]] == ["gamma"]
        assert manager.jobs() == jobs_before
        assert [store.path.read_bytes() for store in stores if store.path.exists()] == bytes_before
        assert manager.health()["active_count"] == active_count
        assert all(not event.is_set() for event in harness.stop_events.values())
    finally:
        coordinator.stop()
        monitor.shutdown()
        manager.shutdown()


def test_reload_keeps_duplicate_room_arbitration_capacity_and_consumed_history(tmp_path):
    coordinator, manager, slots, state = _components(tmp_path)
    manager.start("https://www.tiktok.com/@manual/live", str(tmp_path / "manual.mp4"),
                  expected_room_id="44")
    config = ConfigurationStore(tmp_path / "config.json")
    config.save(Configuration(monitored_creators=("manual", "alias", "beta")))
    rooms = {"manual": "44", "alias": "44", "beta": "2", "gamma": "3"}
    monitor = CreatorMonitor(
        (), creator_loader=lambda: config.load(missing_ok=False).monitored_creators,
        resolver=lambda page: LiveResolution(rooms[page.split("@")[1].split("/")[0]],
                                              "https://cdn.test/live.flv"),
        cycle_completed=coordinator.cycle_completed,
    )
    monitor._poll_cycle()
    assert len(slots[0].starts) == len(slots[1].starts) == 1
    status = coordinator.snapshot(monitor.snapshot())
    results = {item["creator"]: item["automation"] for item in status["creators"]}
    assert results["alias"]["reason"] == "duplicate_live_owned"
    assert results["beta"]["state"] == "started"
    assert state.load().consumed() == {"beta": "2", "manual": "44"}
    owners = manager.jobs()
    config.save(Configuration(monitored_creators=("gamma",)))
    monitor._poll_cycle()
    assert manager.jobs() == owners
    assert coordinator.snapshot(monitor.snapshot())["creators"][0]["automation"]["reason"] == "recording_slot_unavailable"
    config.save(Configuration())
    monitor._poll_cycle()
    assert state.load().consumed() == {"beta": "2", "manual": "44"}
    slots[0].complete()
    config.save(Configuration(monitored_creators=("manual",)))
    monitor._poll_cycle()
    assert len(slots[0].starts) == 1
    assert coordinator.snapshot(monitor.snapshot())["creators"][0]["automation"]["reason"] == "same_room_consumed"
