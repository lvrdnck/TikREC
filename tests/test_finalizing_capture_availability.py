"""Characterize #52's CURRENT synchronous behavior, not the proposed queue.

Real controllers, manager, durable stores, admission and automation are used.
Only capture/media execution is injected; no network, FFmpeg or source media.
These assertions must be replaced by the design's acceptance cases when the
ownership correction is implemented, rather than preserving this limitation.
"""

from datetime import datetime
from threading import Event
from types import SimpleNamespace

import pytest

from tikrec.admission import MINIMUM_FREE_BYTES, RecordingAdmission
from tikrec.automation import AutomationCoordinator
from tikrec.automation_state import AutomationState, AutomationStateStore
from tikrec.capture import CaptureResult, finalize_capture_result
from tikrec.job_state import JobStateStore
from tikrec.lifecycle_lock import LifecycleBusy, acquire_lifecycle
from tikrec.recording import RecordingBusy, RecordingController
from tikrec.recording_manager import RecordingDuplicate, RecordingManager


PAGE = "https://www.tiktok.com/@creator/live"
BETA = "https://www.tiktok.com/@beta/live"


class ControlledSession:
    """Event-controlled fake source/finalizer with a genuine finalizer wait."""

    def __init__(self, room, *, finalizing=True, fail=False):
        self.room, self.finalizing, self.fail = room, finalizing, fail
        self.entered, self.release = Event(), Event()
        self.stop_event = None

    def capture(self, **options):
        """Publish capture identity, then simulate a closed source or active one."""
        self.stop_event = options["stop_event"]
        options["room_identity"](self.room)
        options["state"]("recording")
        if not self.finalizing:
            self.entered.set()
            assert self.release.wait(5), "test capture cleanup deadline"
            return CaptureResult((), options["output_path"])
        options["state"]("finalizing")
        # Parts are names only. The fake encoder does not inspect/write any media.
        parts = (options["parts_directory"] / "part-0001.flv",)
        return finalize_capture_result(parts, options["output_path"],
                                       finalizer=self.finalizer)

    def finalizer(self, parts, output):
        """Block inside the actual finalization helper until the test permits it."""
        assert tuple(parts)
        self.entered.set()
        assert self.release.wait(5), "test finalizer cleanup deadline"
        if self.fail:
            raise RuntimeError("injected encoder failure")
        return output


@pytest.fixture
def controlled(tmp_path):
    sessions = {}

    def capture(url, **options):
        return sessions[options["output_path"].stem].capture(**options)

    stores = tuple(JobStateStore(tmp_path / f"slot-{i}.json") for i in (1, 2))
    manager = RecordingManager(tuple(
        RecordingController(capture=capture, store=store) for store in stores))
    yield manager, stores, sessions
    # Always release our fake sources/encoders before shutdown joins the workers.
    for session in sessions.values():
        session.release.set()
    manager.shutdown()
    assert all(c._worker is None or not c._worker.is_alive()
               for c in manager.controllers)


def start_old(tmp_path, controlled, *, fail=False):
    """Start one real slot and wait for its fake encoder's entered barrier."""
    manager, stores, sessions = controlled
    session = sessions["old"] = ControlledSession("123", fail=fail)
    accepted = manager.start(PAGE, str(tmp_path / "old.mp4"),
                             expected_room_id="123", raw_copy=True)
    assert session.entered.wait(2)
    assert manager.controllers[0].status()["state"] == "finalizing"
    return session, accepted


def cycle(number, state="live"):
    """Represent a complete observed cycle for a distinct returning room."""
    return {"cycle_count": number, "cycle_in_progress": False, "creators": [{
        "creator": "creator", "state": state,
        "room_id": "456" if state == "live" else None,
        "observed_at": float(number), "unknown_reason": None}]}


def coordinator(tmp_path, controlled):
    """Use real admission with deterministic storage and unused output names."""
    manager, _, sessions = controlled
    sessions["creator-return"] = ControlledSession("456", finalizing=False)
    admission = RecordingAdmission(
        tmp_path, manager.health, clock=lambda: datetime(2026, 10, 3, 14),
        disk_usage=lambda _: SimpleNamespace(free=MINIMUM_FREE_BYTES * 2),
        allocator=lambda root, creator, **_: (
            root / "creator-return.mp4", root / "creator-return.parts"))
    store = AutomationStateStore(tmp_path / "automation.json")
    store.save(AutomationState(consumed_rooms=(("creator", "123"),)))
    return AutomationCoordinator(manager, admission, store,
                                 automatic_raw_copy_creators=("creator",)), store


def test_finalizing_slot_and_page_reject_new_room_despite_free_second_slot(
        tmp_path, controlled):
    manager, stores, sessions = controlled
    old, accepted = start_old(tmp_path, controlled)
    health = manager.health()
    assert (health["active_count"], health["available_slots"]) == (1, 1)
    durable = stores[0].load()
    assert durable.session_id == accepted["session_id"]
    assert durable.state == "finalizing" and durable.raw_copy_enabled
    assert not durable.stop_requested and not durable.finalization_completed
    with pytest.raises(RecordingDuplicate, match="page already owned"):
        manager.start(PAGE, str(tmp_path / "return.mp4"), expected_room_id="456")
    # LIVE and artifact guards currently share the same owner, independently of capacity.
    with pytest.raises(ValueError, match="output is already owned"):
        manager.start(BETA, str(tmp_path / "old.mp4"), expected_room_id="789")
    with pytest.raises(LifecycleBusy):
        with acquire_lifecycle(tmp_path, "retention"):
            pytest.fail("finalizing writer unexpectedly released retention protection")
    assert stores[0].load() == durable and not old.stop_event.is_set()
    sessions["beta"] = ControlledSession("789", finalizing=False)
    second = manager.start(BETA, str(tmp_path / "beta.mp4"), expected_room_id="789")
    assert sessions["beta"].entered.wait(2)
    assert second["slot_id"] == "slot-2"
    assert second["session_id"] != accepted["session_id"]


def test_two_finalizing_jobs_consume_both_capture_slots(tmp_path, controlled):
    manager, stores, sessions = controlled
    start_old(tmp_path, controlled)
    sessions["beta"] = ControlledSession("789")
    manager.start(BETA, str(tmp_path / "beta.mp4"), expected_room_id="789")
    assert sessions["beta"].entered.wait(2)
    assert all(store.load().state == "finalizing" for store in stores)
    assert manager.health()["available_slots"] == 0
    with pytest.raises(RecordingBusy, match="capacity is unavailable"):
        manager.start("https://www.tiktok.com/@gamma/live",
                      str(tmp_path / "gamma.mp4"), expected_room_id="987")


@pytest.mark.parametrize("fail", [False, True], ids=["completed", "failed"])
def test_duplicate_is_not_consumed_and_retries_only_at_later_cycle(
        tmp_path, controlled, fail):
    manager, stores, sessions = controlled
    old, accepted = start_old(tmp_path, controlled, fail=fail)
    automation, store = coordinator(tmp_path, controlled)
    for number in (1, 2):
        observed = cycle(number)
        automation.cycle_completed(observed)
        result = automation.snapshot(observed)["creators"][0]["automation"]
        assert (result["state"], result["reason"]) == (
            "suppressed", "duplicate_live_owned")
        assert store.load().consumed() == {"creator": "123"}
        assert store.load().pending_claim is None
        assert not sessions["creator-return"].entered.is_set()
    old.release.set()
    manager.controllers[0]._worker.join(2)
    assert not manager.controllers[0]._worker.is_alive()
    assert stores[0].load().state == ("failed" if fail else "completed")
    assert manager.health()["available_slots"] == 2
    # Settlement has no immediate monitoring callback; an already-processed cycle is a no-op.
    automation.cycle_completed(cycle(2))
    assert not sessions["creator-return"].entered.is_set()
    automation.cycle_completed(cycle(3))
    assert sessions["creator-return"].entered.wait(2)
    started = manager.controllers[0].status()
    assert started["session_id"] != accepted["session_id"]
    assert started["room_id"] == "456" and started["raw_copy_enabled"]
    assert store.load().consumed() == {"creator": "456"}
    assert store.load().pending_claim is None
    automation.cycle_completed(cycle(4))
    result = automation.snapshot(cycle(4))["creators"][0]["automation"]
    assert result["reason"] == "same_room_consumed"
    assert manager.health()["active_count"] == 1


def test_returning_room_that_ends_before_release_is_never_started(
        tmp_path, controlled):
    manager, _, sessions = controlled
    old, _ = start_old(tmp_path, controlled)
    automation, store = coordinator(tmp_path, controlled)
    automation.cycle_completed(cycle(1))
    assert store.load().consumed() == {"creator": "123"}
    automation.cycle_completed(cycle(2, "offline"))
    assert store.load().consumed() == {}
    old.release.set()
    manager.controllers[0]._worker.join(2)
    assert not manager.controllers[0]._worker.is_alive()
    automation.cycle_completed(cycle(3, "offline"))
    assert not sessions["creator-return"].entered.is_set()
    assert manager.health()["available_slots"] == 2
