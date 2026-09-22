"""Deterministic cycle-level automatic-start coordinator tests."""

from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from tikrec.automation import AutomationCoordinator
from tikrec.admission import MINIMUM_FREE_BYTES, RecordingAdmission
from tikrec.automation_state import AutomationStateStore
from tikrec.recording import RecordingBusy


class Controller:
    def __init__(self, *, status=None, failure=None):
        self.current = status or {"state": "idle", "active": False}
        self.failure = failure
        self.starts = []

    def status(self):
        return dict(self.current)

    def start(self, url, output, **options):
        self.starts.append((url, output, options))
        if self.failure is not None:
            raise self.failure
        session_id = f"00000000-0000-0000-0000-{len(self.starts):012d}"
        self.current = {
            "state": "resolving", "active": True, "source_url": url,
            "output_path": output,
            "parts_directory": str(Path(output).with_suffix(".parts")),
            "room_id": None, "session_id": session_id,
        }
        return dict(self.current)


class Admission:
    def __init__(self, root: Path, *, states=None, candidates=None):
        self.root = root
        self.states = states or {}
        self.candidates = list(candidates or [])
        self.calls = 0

    def evaluate(self, monitoring):
        self.calls += 1
        snapshot = dict(monitoring)
        creators = []
        for item in monitoring.get("creators", []):
            value = dict(item)
            state, reason = self.states.get(
                item["creator"],
                ("ready", None) if item.get("state") == "live"
                else ("not_applicable", None),
            )
            output = None
            parts = None
            if state == "ready":
                if self.candidates:
                    output = Path(self.candidates[min(self.calls - 1, len(self.candidates) - 1)])
                else:
                    output = self.root / f"{item['creator']}-20260922-120000.mp4"
                parts = output.with_suffix(".parts")
            value["admission"] = {
                "state": state, "reason": reason,
                "free_bytes": 10 * 1024**3,
                "output_path": None if output is None else str(output),
                "parts_directory": None if parts is None else str(parts),
            }
            creators.append(value)
        snapshot["creators"] = creators
        snapshot["minimum_free_bytes"] = 10 * 1024**3
        return snapshot


def _cycle(number: int, *observations) -> dict:
    return {
        "cycle_count": number,
        "cycle_in_progress": False,
        "creators": [
            {
                "creator": creator, "state": state,
                "room_id": room_id, "observed_at": float(number),
                "unknown_reason": None,
            }
            for creator, state, room_id in observations
        ],
    }


def _coordinator(tmp_path: Path, controller=None, admission=None):
    controller = controller or Controller()
    admission = admission or Admission(tmp_path)
    store = AutomationStateStore(tmp_path / "automation.json")
    return AutomationCoordinator(controller, admission, store), controller, admission, store


def test_one_ready_creator_starts_once_after_complete_cycle(tmp_path: Path):
    coordinator, controller, admission, store = _coordinator(tmp_path)
    cycle = _cycle(1, ("creator", "live", "123"))
    coordinator.cycle_completed(cycle)
    coordinator.cycle_completed(cycle)
    assert len(controller.starts) == 1
    url, output, options = controller.starts[0]
    assert url == "https://www.tiktok.com/@creator/live"
    assert output.endswith("creator-20260922-120000.mp4")
    assert options == {"expected_room_id": "123"}
    assert admission.calls == 2
    assert store.load().consumed() == {"creator": "123"}
    assert store.load().pending_claim is None
    status = coordinator.snapshot(cycle)
    assert status["automation"]["started_creator"] == "creator"
    assert status["creators"][0]["automation"]["state"] == "started"


def test_candidate_is_reallocated_immediately_before_start(tmp_path: Path):
    first = tmp_path / "creator-20260922-120000.mp4"
    second = tmp_path / "creator-20260922-120000-2.mp4"
    admission = Admission(tmp_path, candidates=(first, second))
    coordinator, controller, _, _ = _coordinator(tmp_path, admission=admission)
    coordinator.cycle_completed(_cycle(1, ("creator", "live", "123")))
    assert controller.starts[0][1] == str(second)


def test_new_collision_between_evaluations_selects_fresh_suffix(tmp_path: Path):
    controller = Controller()
    policy = RecordingAdmission(
        tmp_path, lambda: {"available": True},
        clock=lambda: datetime(2026, 9, 22, 12, 0, 0),
        disk_usage=lambda _: SimpleNamespace(free=MINIMUM_FREE_BYTES),
    )

    class CollidingAdmission:
        calls = 0

        def evaluate(self, monitoring):
            self.calls += 1
            result = policy.evaluate(monitoring)
            if self.calls == 1:
                Path(result["creators"][0]["admission"]["output_path"]).write_bytes(
                    b"external owner"
                )
            return result

    coordinator, _, _, _ = _coordinator(
        tmp_path, controller=controller, admission=CollidingAdmission()
    )
    coordinator.cycle_completed(_cycle(1, ("creator", "live", "123")))
    assert Path(controller.starts[0][1]).name == "creator-20260922-120000-2.mp4"
    assert (tmp_path / "creator-20260922-120000.mp4").read_bytes() == b"external owner"


@pytest.mark.parametrize("failure,reason", [
    (RecordingBusy("manual won race"), "start_rejected_busy"),
    (ValueError("fresh output collision"), "start_rejected"),
])
def test_controller_remains_authoritative_and_rejected_claim_is_cleared(
    tmp_path: Path, failure: Exception, reason: str
):
    controller = Controller(failure=failure)
    coordinator, _, _, store = _coordinator(tmp_path, controller=controller)
    cycle = _cycle(
        1, ("zeta", "live", "2"), ("alpha", "live", "1")
    )
    coordinator.cycle_completed(cycle)
    assert len(controller.starts) == 1
    assert "@alpha/live" in controller.starts[0][0]
    assert store.load().pending_claim is None
    status = coordinator.snapshot(cycle)
    values = {item["creator"]: item["automation"] for item in status["creators"]}
    assert values["alpha"] == {
        "state": "failed", "reason": reason,
        "armed": True, "consumed_room_id": None,
    }
    assert values["zeta"]["reason"] == "prior_start_attempt_failed"


def test_same_room_is_consumed_across_cycles_and_manual_stop(tmp_path: Path):
    coordinator, controller, _, _ = _coordinator(tmp_path)
    coordinator.cycle_completed(_cycle(1, ("creator", "live", "123")))
    controller.current.update(state="completed", active=False)
    coordinator.cycle_completed(_cycle(2, ("creator", "live", "123")))
    assert len(controller.starts) == 1
    status = coordinator.snapshot(_cycle(2, ("creator", "live", "123")))
    assert status["creators"][0]["automation"]["reason"] == "same_room_consumed"


def test_offline_rearms_same_room_but_unknown_does_not(tmp_path: Path):
    coordinator, controller, _, store = _coordinator(tmp_path)
    coordinator.cycle_completed(_cycle(1, ("creator", "live", "123")))
    controller.current.update(state="completed", active=False)
    coordinator.cycle_completed(_cycle(2, ("creator", "unknown", None)))
    coordinator.cycle_completed(_cycle(3, ("creator", "live", "123")))
    assert len(controller.starts) == 1
    coordinator.cycle_completed(_cycle(4, ("creator", "offline", None)))
    assert store.load().consumed() == {}
    coordinator.cycle_completed(_cycle(5, ("creator", "live", "123")))
    assert len(controller.starts) == 2


def test_different_room_is_eligible_without_intermediate_offline(tmp_path: Path):
    coordinator, controller, _, store = _coordinator(tmp_path)
    coordinator.cycle_completed(_cycle(1, ("creator", "live", "123")))
    controller.current.update(state="completed", active=False)
    coordinator.cycle_completed(_cycle(2, ("creator", "live", "456")))
    assert len(controller.starts) == 2
    assert controller.starts[-1][2]["expected_room_id"] == "456"
    assert store.load().consumed() == {"creator": "456"}


def test_lexical_order_drives_multiple_accepted_starts_with_compatible_fake(
    tmp_path: Path,
):
    coordinator, controller, _, _ = _coordinator(tmp_path)
    cycle = _cycle(
        1, ("zeta", "live", "2"), ("alpha", "live", "1")
    )
    coordinator.cycle_completed(cycle)
    assert [item[0].split("@")[1].split("/")[0] for item in controller.starts] == [
        "alpha", "zeta",
    ]
    status = coordinator.snapshot(cycle)
    values = {item["creator"]: item["automation"] for item in status["creators"]}
    assert values["alpha"]["state"] == values["zeta"]["state"] == "started"
    assert status["automation"]["selected_creators"] == ["alpha", "zeta"]
    assert status["automation"]["selected_creator"] is None


def test_busy_cycle_is_not_queued_and_later_cycle_can_start(tmp_path: Path):
    admission = Admission(
        tmp_path, states={"creator": ("skipped", "recording_slot_unavailable")}
    )
    coordinator, controller, _, _ = _coordinator(tmp_path, admission=admission)
    coordinator.cycle_completed(_cycle(1, ("creator", "live", "123")))
    assert controller.starts == []
    admission.states.clear()
    coordinator.cycle_completed(_cycle(2, ("creator", "live", "123")))
    assert len(controller.starts) == 1


@pytest.mark.parametrize("state,reason", [
    ("blocked", "output_directory_unconfigured"),
    ("blocked", "storage_unavailable"),
    ("blocked", "low_free_space"),
    ("skipped", "recording_slot_unavailable"),
])
def test_admission_failures_never_start(tmp_path: Path, state: str, reason: str):
    admission = Admission(tmp_path, states={"creator": (state, reason)})
    coordinator, controller, _, _ = _coordinator(tmp_path, admission=admission)
    coordinator.cycle_completed(_cycle(1, ("creator", "live", "123")))
    assert controller.starts == []
    status = coordinator.snapshot(_cycle(1, ("creator", "live", "123")))
    assert status["creators"][0]["automation"]["reason"] == reason


def test_existing_manual_job_for_same_room_consumes_duplicate(tmp_path: Path):
    output = tmp_path / "manual.mp4"
    controller = Controller(status={
        "state": "recording", "active": True,
        "source_url": "https://www.tiktok.com/@creator/live",
        "output_path": str(output), "parts_directory": str(tmp_path / "manual.parts"),
        "room_id": "123",
    })
    coordinator, _, _, store = _coordinator(tmp_path, controller=controller)
    coordinator.cycle_completed(_cycle(1, ("creator", "live", "123")))
    assert controller.starts == []
    assert store.load().consumed() == {"creator": "123"}


def test_stop_prevents_later_automatic_start(tmp_path: Path):
    coordinator, controller, _, _ = _coordinator(tmp_path)
    coordinator.stop()
    coordinator.cycle_completed(_cycle(1, ("creator", "live", "123")))
    assert controller.starts == []
    assert coordinator.snapshot(_cycle(1, ("creator", "live", "123")))[
        "automation"
    ]["blocked_reason"] == "service_shutting_down"
