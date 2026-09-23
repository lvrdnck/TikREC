"""Capacity-aware automatic recording tests with two independent fake slots."""

from datetime import datetime
from pathlib import Path
from threading import Event
from types import SimpleNamespace

from tikrec.admission import MINIMUM_FREE_BYTES, RecordingAdmission
from tikrec.automation import AutomationCoordinator
from tikrec.automation_state import (
    AutomationState,
    AutomationStateStore,
    PendingAutomaticStart,
)
from tikrec.recording_manager import RecordingManager
from tikrec.recording import RecordingController
from tikrec.capture import CaptureResult
from tests.test_automation import _cycle


class Slot:
    """Expose one deterministic controller contract without launching workers."""

    def __init__(self, identity):
        self.identity = identity
        self.starts = []
        self.current = {"state": "idle", "active": False}
        self.closed = False

    def status(self):
        return dict(self.current)

    def health(self):
        return {
            "available": not self.current.get("active", False) and not self.closed,
            "active": self.current.get("active", False),
            "shutting_down": self.closed,
            "recovery_state": self.current.get("recovery_state"),
            "recovery_reason": self.current.get("recovery_reason"),
        }

    def start(self, url, output, **options):
        self.starts.append((url, output, options))
        number = self.identity + len(self.starts)
        self.current = {
            "state": "recording", "active": True,
            "session_id": f"00000000-0000-0000-0000-{number:012d}",
            "source_url": url, "output_path": output,
            "parts_directory": str(Path(output).with_suffix(".parts")),
            "room_id": options.get("expected_room_id"), "started_at": float(number),
        }
        return dict(self.current)

    def stop(self):
        self.current["stop_requested"] = True
        return dict(self.current)

    def complete(self):
        self.current.update(state="completed", active=False)

    def shutdown(self):
        self.closed = True
        self.current["active"] = False


def _components(tmp_path):
    slots = (Slot(100), Slot(200))
    manager = RecordingManager(slots)
    admission = RecordingAdmission(
        tmp_path, manager.health,
        clock=lambda: datetime(2026, 9, 22, 12, 0, 0),
        disk_usage=lambda _: SimpleNamespace(free=MINIMUM_FREE_BYTES),
    )
    store = AutomationStateStore(tmp_path / "automation.json")
    return AutomationCoordinator(manager, admission, store), manager, slots, store


def test_two_lexical_starts_fill_capacity_and_third_is_reconsidered(tmp_path):
    coordinator, manager, slots, store = _components(tmp_path)
    first_cycle = _cycle(
        1, ("zeta", "live", "3"), ("beta", "live", "2"),
        ("alpha", "live", "1"),
    )
    coordinator.cycle_completed(first_cycle)
    assert [slots[0].starts[0][0], slots[1].starts[0][0]] == [
        "https://www.tiktok.com/@alpha/live",
        "https://www.tiktok.com/@beta/live",
    ]
    status = coordinator.snapshot(first_cycle)
    automatic = status["automation"]
    assert automatic["selected_creators"] == ["alpha", "beta"]
    assert [item["creator"] for item in automatic["started_recordings"]] == [
        "alpha", "beta",
    ]
    assert automatic["started_creator"] is None
    values = {item["creator"]: item["automation"] for item in status["creators"]}
    assert values["zeta"]["reason"] == "capacity_exhausted"
    assert store.load().consumed() == {"alpha": "1", "beta": "2"}
    assert manager.health()["active_count"] == 2

    slots[0].complete()
    second_cycle = _cycle(
        2, ("zeta", "live", "3"), ("beta", "live", "2"),
        ("alpha", "live", "1"),
    )
    coordinator.cycle_completed(second_cycle)
    assert slots[0].starts[-1][0] == "https://www.tiktok.com/@zeta/live"
    assert store.load().consumed() == {"alpha": "1", "beta": "2", "zeta": "3"}


def test_manual_same_room_suppresses_duplicate_while_other_creator_starts(tmp_path):
    coordinator, manager, slots, store = _components(tmp_path)
    manual = manager.start(
        "https://www.tiktok.com/@manual/live", str(tmp_path / "manual.mp4"),
        expected_room_id="44",
    )
    cycle = _cycle(1, ("manual", "live", "44"), ("alpha", "live", "1"))
    coordinator.cycle_completed(cycle)
    assert slots[0].current["session_id"] == manual["session_id"]
    assert len(slots[0].starts) == 1
    assert slots[1].starts[0][0] == "https://www.tiktok.com/@alpha/live"
    assert store.load().consumed() == {"alpha": "1", "manual": "44"}
    status = coordinator.snapshot(cycle)
    values = {item["creator"]: item["automation"] for item in status["creators"]}
    assert values["manual"]["reason"] == "same_room_consumed"
    assert values["alpha"]["state"] == "started"


def test_consumed_and_offline_rearm_remain_independent_per_creator(tmp_path):
    coordinator, _, slots, store = _components(tmp_path)
    coordinator.cycle_completed(_cycle(
        1, ("alpha", "live", "1"), ("beta", "live", "2")
    ))
    slots[0].complete()
    slots[1].complete()
    coordinator.cycle_completed(_cycle(
        2, ("alpha", "offline", None), ("beta", "live", "2")
    ))
    assert store.load().consumed() == {"beta": "2"}
    coordinator.cycle_completed(_cycle(
        3, ("alpha", "live", "1"), ("beta", "live", "2")
    ))
    assert len(slots[0].starts) == 2 and len(slots[1].starts) == 1
    assert store.load().consumed() == {"alpha": "1", "beta": "2"}


def test_pending_claim_reconciles_against_matching_second_job(tmp_path):
    _, manager, slots, store = _components(tmp_path)
    manager.start(
        "https://www.tiktok.com/@other/live", str(tmp_path / "other.mp4"),
        expected_room_id="9",
    )
    output = tmp_path / "creator.mp4"
    manager.start(
        "https://www.tiktok.com/@creator/live", str(output), expected_room_id="123"
    )
    claim = PendingAutomaticStart(
        "creator", "123", str(output), str(output.with_suffix(".parts"))
    )
    store.save(AutomationState(pending_claim=claim))
    recovered = AutomationCoordinator(
        manager,
        RecordingAdmission(
            tmp_path, manager.health,
            clock=lambda: datetime(2026, 9, 22, 12, 0, 0),
            disk_usage=lambda _: SimpleNamespace(free=MINIMUM_FREE_BYTES),
        ),
        store,
    )
    assert slots[1].current["source_url"].endswith("/@creator/live")
    assert store.load() == AutomationState((("creator", "123"),))
    assert recovered.snapshot(_cycle(0))["automation"]["operational"] is True


def test_simultaneous_names_are_distinct_and_create_no_reservations(tmp_path):
    coordinator, _, slots, _ = _components(tmp_path)
    coordinator.cycle_completed(_cycle(
        1, ("alpha", "live", "1"), ("beta", "live", "2")
    ))
    outputs = [Path(slot.starts[0][1]) for slot in slots]
    assert outputs[0].name == "alpha-20260922-120000.mp4"
    assert outputs[1].name == "beta-20260922-120000.mp4"
    assert outputs[0] != outputs[1]
    assert all(not output.exists() and not output.with_suffix(".parts").exists()
               for output in outputs)


def _resolving_components(tmp_path):
    """Hold real controller workers before they can publish a resolved room."""
    entered = {name: Event() for name in (
        "manual", "alpha-20260923-120000", "gamma-20260923-120000",
        "zeta-20260923-120000",
    )}
    def capture(url, **kwargs):
        name = kwargs["output_path"].stem
        entered.setdefault(name, Event()).set()
        assert kwargs["stop_event"].wait(3)
        return CaptureResult((), None, True)
    manager = RecordingManager((RecordingController(capture=capture),
                                RecordingController(capture=capture)))
    admission = RecordingAdmission(
        tmp_path, manager.health,
        clock=lambda: datetime(2026, 9, 23, 12, 0, 0),
        disk_usage=lambda _: SimpleNamespace(free=MINIMUM_FREE_BYTES),
    )
    store = AutomationStateStore(tmp_path / "automation.json")
    return AutomationCoordinator(manager, admission, store), manager, entered, store


def test_manual_resolving_same_page_is_suppressed_without_claim(tmp_path):
    coordinator, manager, entered, store = _resolving_components(tmp_path)
    manual = manager.start("https://www.tiktok.com/@alpha/live",
                           str(tmp_path / "manual.mp4"))
    assert entered["manual"].wait(2)
    assert manager.status()["room_id"] is None
    try:
        cycle = _cycle(1, ("alpha", "live", "123"))
        coordinator.cycle_completed(cycle)
        assert manager.health()["active_count"] == 1
        assert manager.status()["session_id"] == manual["session_id"]
        assert manager.status()["stop_requested"] is False
        assert store.load().pending_claim is None
        assert store.load().consumed() == {}
        assert coordinator.snapshot(cycle)["creators"][0]["automation"]["reason"] == "duplicate_live_owned"
    finally:
        manager.shutdown()


def test_duplicate_candidate_does_not_starve_unrelated_creator(tmp_path):
    coordinator, manager, entered, store = _resolving_components(tmp_path)
    manual = manager.start("https://www.tiktok.com/@alpha/live",
                           str(tmp_path / "manual.mp4"))
    assert entered["manual"].wait(2)
    try:
        cycle = _cycle(1, ("zeta", "live", "456"), ("alpha", "live", "123"))
        coordinator.cycle_completed(cycle)
        assert entered["zeta-20260923-120000"].wait(2)
        assert manager.health()["active_count"] == 2
        assert manager.controllers[0].status()["session_id"] == manual["session_id"]
        assert store.load().pending_claim is None
        assert store.load().consumed() == {"zeta": "456"}
        values = {item["creator"]: item["automation"] for item in coordinator.snapshot(cycle)["creators"]}
        assert values["alpha"]["reason"] == "duplicate_live_owned"
        assert values["zeta"]["state"] == "started"
    finally:
        manager.shutdown()


def test_two_automatic_creators_in_same_room_use_only_one_slot(tmp_path):
    coordinator, manager, entered, store = _resolving_components(tmp_path)
    try:
        cycle = _cycle(1, ("gamma", "live", "456"),
                       ("beta", "live", "123"), ("alpha", "live", "123"))
        coordinator.cycle_completed(cycle)
        assert entered["alpha-20260923-120000"].wait(2)
        assert entered["gamma-20260923-120000"].wait(2)
        assert manager.health()["active_count"] == 2
        assert [item["source_url"] for item in manager.recordings()["slots"]] == [
            "https://www.tiktok.com/@alpha/live",
            "https://www.tiktok.com/@gamma/live",
        ]
        assert store.load().pending_claim is None
        assert store.load().consumed() == {"alpha": "123", "gamma": "456"}
        values = {item["creator"]: item["automation"] for item in coordinator.snapshot(cycle)["creators"]}
        assert values["beta"]["reason"] == "duplicate_live_owned"
        assert values["gamma"]["state"] == "started"
    finally:
        manager.shutdown()
