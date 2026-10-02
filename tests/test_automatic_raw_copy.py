"""Per-creator automatic evidence selection with real independent controllers."""

import json
from datetime import datetime
from threading import Event
from types import SimpleNamespace

import pytest

from tikrec.admission import MINIMUM_FREE_BYTES, RecordingAdmission
from tikrec.automation import AutomationCoordinator
from tikrec.automation_state import AutomationStateStore
from tikrec.automatic_identity import expected_room_resolvers
from tikrec.capture import CaptureResult
from tikrec.configuration import Configuration, ConfigurationStore
from tikrec.creator_identity import CreatorIdentityError
from tikrec.job_state import JobStateStore
from tikrec.live import capture_live
from tikrec.monitoring import CreatorMonitor
from tikrec.recording import RecordingController
from tikrec.recording_manager import RecordingManager
from tikrec.tiktok import TikTokOfflineError
from tikrec.tiktok_identity import LiveResolution
from tests.test_automation import Admission, Controller, _cycle
from tests.test_automation_capacity import Slot
from tests.test_live import stream


def coordinator(tmp_path, manager, raw=()):
    admission = RecordingAdmission(
        tmp_path, manager.health, clock=lambda: datetime(2026, 10, 2),
        disk_usage=lambda _: SimpleNamespace(free=MINIMUM_FREE_BYTES))
    store = AutomationStateStore(tmp_path / "automation.json")
    return AutomationCoordinator(manager, admission, store,
                                 automatic_raw_copy_creators=raw), store


def test_default_and_one_creator_boolean_bind_at_accepted_start(tmp_path):
    controller = Controller()
    automatic = AutomationCoordinator(controller, Admission(tmp_path),
                                     AutomationStateStore(tmp_path / "automation.json"),
                                     automatic_raw_copy_creators=("alpha",))
    automatic.cycle_completed(_cycle(1, ("alpha", "live", "1")))
    assert controller.starts[0][2] == {"raw_copy": True, "expected_room_id": "1"}
    controller.current.update(state="completed", active=False)
    automatic.cycle_completed(_cycle(2, ("beta", "live", "2")))
    assert controller.starts[1][2] == {"raw_copy": False, "expected_room_id": "2"}


@pytest.mark.parametrize("value", [["alpha"], ("Alpha",), ("alpha", "alpha")])
def test_coordinator_rejects_noncanonical_startup_policy_without_state_mutation(tmp_path, value):
    store = AutomationStateStore(tmp_path / "automation.json")
    with pytest.raises(CreatorIdentityError):
        AutomationCoordinator(Controller(), Admission(tmp_path), store,
                              automatic_raw_copy_creators=value)
    assert not store.path.exists()


def test_two_real_workers_keep_independent_flags_through_preference_and_monitor_changes(tmp_path):
    calls, entered = {}, {name: Event() for name in ("alpha", "beta")}

    def capture(page, **options):
        name = page.split("@")[1].split("/")[0]
        calls[name] = options
        options["state"]("recording")
        entered[name].set()
        assert options["stop_event"].wait(5)
        return CaptureResult((), None, True)

    stores = (JobStateStore(tmp_path / "job.json"), JobStateStore(tmp_path / "job-2.json"))
    manager = RecordingManager(tuple(RecordingController(capture=capture, store=s) for s in stores))
    config = ConfigurationStore(tmp_path / "config.json")
    config.save(Configuration(monitored_creators=("alpha", "beta"),
                              automatic_raw_copy_creators=("alpha",)))
    automatic, state = coordinator(tmp_path, manager, config.load().automatic_raw_copy_creators)
    rooms = {"alpha": "1", "beta": "2", "gamma": "3"}
    monitor = CreatorMonitor(
        (), creator_loader=lambda: config.load(missing_ok=False).monitored_creators,
        resolver=lambda page: LiveResolution(rooms[page.split("@")[1].split("/")[0]], "https://cdn.test/live"),
        cycle_completed=automatic.cycle_completed)
    try:
        monitor._poll_cycle()
        assert all(event.wait(2) for event in entered.values())
        assert calls["alpha"]["raw_copy_dir"] == calls["alpha"]["parts_directory"]
        assert "raw_copy_dir" not in calls["beta"]
        assert stores[0].load().raw_copy_enabled is True
        assert stores[1].load().raw_copy_enabled is False
        identities = [s.load().session_id for s in stores]
        before = [s.path.read_bytes() for s in stores]
        assert manager.health()["active_count"] == 2
        config.save(Configuration(automatic_raw_copy_creators=("beta",)))
        monitor._poll_cycle()
        assert monitor.snapshot()["creators"] == []
        assert monitor.snapshot()["configuration"]["state"] == "ok"
        config.save(Configuration(monitored_creators=("alpha", "beta", "gamma"),
                                  automatic_raw_copy_creators=("beta",)))
        monitor._poll_cycle()
        status = automatic.snapshot(monitor.snapshot())
        reasons = {item["creator"]: item["automation"]["reason"] for item in status["creators"]}
        assert reasons == {"alpha": "same_room_consumed", "beta": "same_room_consumed",
                           "gamma": "recording_slot_unavailable"}
        assert [s.path.read_bytes() for s in stores] == before
        assert [s.load().session_id for s in stores] == identities
        assert all(not item["stop_event"].is_set() for item in calls.values())
        assert state.load().consumed() == {"alpha": "1", "beta": "2"}
    finally:
        automatic.stop()
        monitor.shutdown()
        manager.shutdown()


def test_duplicate_room_capacity_and_offline_rearm_with_raw_copy(tmp_path):
    slots = (Slot(100), Slot(200))
    manager = RecordingManager(slots)
    automatic, state = coordinator(tmp_path, manager, ("alias", "beta"))
    manager.start("https://www.tiktok.com/@manual/live", str(tmp_path / "manual.mp4"), expected_room_id="1")
    automatic.cycle_completed(_cycle(1, ("alias", "live", "1"), ("beta", "live", "2"),
                                    ("gamma", "live", "3")))
    assert len(slots[0].starts) == len(slots[1].starts) == 1
    assert slots[1].starts[0][2] == {"raw_copy": True, "expected_room_id": "2"}
    assert "alias" not in state.load().consumed()
    slots[1].complete()
    restarted, _ = coordinator(tmp_path, manager, ())
    restarted.cycle_completed(_cycle(2, ("beta", "live", "2")))
    assert len(slots[1].starts) == 1
    restarted.cycle_completed(_cycle(3, ("beta", "offline", None)))
    restarted.cycle_completed(_cycle(4, ("beta", "live", "2")))
    assert len(slots[1].starts) == 2
    assert slots[1].starts[1][2] == {"raw_copy": False, "expected_room_id": "2"}


@pytest.mark.parametrize("opt_in", [False, True])
def test_automatic_worker_writes_existing_raw_arrival_contract_in_matching_parts(tmp_path, opt_in):
    payload = b"untouched injected source bytes"

    def raw_source(_, raw):
        raw.write(payload)
        return iter(stream())

    def finalizer(parts, output):
        assert tuple(parts)
        output.write_bytes(b"offline finalizer")
        return output

    def capture(page, **options):
        assert "resolver" in options and "bound_resolver" in options
        options["retry_policy"] = None
        return capture_live(page, **options, tag_source=lambda _: iter(stream()),
                            raw_tag_source=raw_source, finalizer=finalizer,
                            media_inspector=lambda _: None, sleeper=lambda _: None,
                            offline_confirmation_checks=1)

    def resolvers(room):
        def offline(*_):
            raise TikTokOfflineError("ended")
        return expected_room_resolvers(room,
            resolver=lambda _: LiveResolution(room, "https://cdn.test/offline"),
            bound_resolver=offline)

    store = JobStateStore(tmp_path / "job.json")
    worker = RecordingController(capture=capture, store=store, automatic_resolvers=resolvers)
    manager = RecordingManager((worker,))
    automatic, _ = coordinator(tmp_path, manager, ("alpha",) if opt_in else ())
    try:
        automatic.cycle_completed(_cycle(1, ("alpha", "live", "1")))
        worker._worker.join(2)
        assert not worker._worker.is_alive()
        assert worker.status()["state"] == "completed"
        assert store.load().raw_copy_enabled is opt_in
        parts = tmp_path / "alpha-20261002-000000.parts"
        assert str(parts) == store.load().parts_directory
        records = [json.loads(line) for line in (parts / "connections.jsonl").read_text().splitlines()]
        raw = parts / "connection-0001.raw"
        arrivals = parts / "connection-0001.arrivals.jsonl"
        if opt_in:
            assert raw.read_bytes() == payload
            assert json.loads(arrivals.read_text().splitlines()[1])["count"] == len(payload)
            assert records[0]["raw_copy"] == raw.name
            assert records[0]["raw_arrivals"] == arrivals.name
        else:
            assert not raw.exists() and not arrivals.exists()
            assert records[0]["raw_copy"] is None
    finally:
        manager.shutdown()
