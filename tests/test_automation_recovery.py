"""Crash-window and fail-closed automatic-start recovery tests."""

from dataclasses import replace
import json
from pathlib import Path

from tikrec.automation import AutomationCoordinator
from tikrec.automation_state import (
    AutomationState,
    AutomationStateStore,
    PendingAutomaticStart,
)
from tikrec.recording import RecordingBusy
from tests.test_automation import Admission, Controller, _cycle


def _claim(tmp_path: Path) -> PendingAutomaticStart:
    output = tmp_path / "creator-20260922-120000.mp4"
    return PendingAutomaticStart(
        "creator", "123", str(output), str(output.with_suffix(".parts"))
    )


class FailingStore:
    """Keep the last durable value and fail selected atomic replacements."""

    def __init__(self, state=AutomationState(), *, fail_saves=()):
        self.state = state
        self.fail_saves = set(fail_saves)
        self.save_count = 0

    def load(self):
        return self.state

    def save(self, state):
        self.save_count += 1
        if self.save_count in self.fail_saves:
            raise OSError("fixed test failure")
        self.state = state


def test_consumed_room_survives_coordinator_restart(tmp_path: Path):
    store = AutomationStateStore(tmp_path / "automation.json")
    first = Controller()
    coordinator = AutomationCoordinator(first, Admission(tmp_path), store)
    coordinator.cycle_completed(_cycle(1, ("creator", "live", "123")))
    first.current = {"state": "completed", "active": False}

    second = Controller(status={"state": "completed", "active": False})
    restarted = AutomationCoordinator(second, Admission(tmp_path), store)
    restarted.cycle_completed(_cycle(2, ("creator", "live", "123")))
    assert second.starts == []
    assert store.load().consumed() == {"creator": "123"}


def test_pending_claim_matching_durable_job_is_promoted(tmp_path: Path):
    claim = _claim(tmp_path)
    store = AutomationStateStore(tmp_path / "automation.json")
    store.save(AutomationState(pending_claim=claim))
    controller = Controller(status={
        "state": "resolving", "active": True,
        "source_url": "https://www.tiktok.com/@creator/live",
        "output_path": claim.output_path,
        "parts_directory": claim.parts_directory,
    })
    coordinator = AutomationCoordinator(controller, Admission(tmp_path), store)
    assert store.load() == AutomationState((("creator", "123"),))
    assert coordinator.snapshot(_cycle(0))["automation"]["operational"] is True


def test_pending_claim_with_idle_controller_is_cleared(tmp_path: Path):
    claim = _claim(tmp_path)
    store = AutomationStateStore(tmp_path / "automation.json")
    store.save(AutomationState(pending_claim=claim))
    coordinator = AutomationCoordinator(Controller(), Admission(tmp_path), store)
    assert store.load() == AutomationState()
    assert coordinator.snapshot(_cycle(0))["automation"]["operational"] is True


def test_pending_claim_with_unchanged_prior_job_is_cleared(tmp_path: Path):
    previous = "00000000-0000-0000-0000-000000000111"
    claim = replace(_claim(tmp_path), previous_session_id=previous)
    store = AutomationStateStore(tmp_path / "automation.json")
    store.save(AutomationState(pending_claim=claim))
    old = tmp_path / "old.mp4"
    controller = Controller(status={
        "state": "completed", "active": False, "session_id": previous,
        "source_url": "https://www.tiktok.com/@old/live",
        "output_path": str(old),
        "parts_directory": str(old.with_suffix(".parts")),
    })
    coordinator = AutomationCoordinator(controller, Admission(tmp_path), store)
    assert store.load() == AutomationState()
    assert coordinator.snapshot(_cycle(0))["automation"]["operational"] is True


def test_pending_claim_with_ambiguous_job_disables_automation(tmp_path: Path):
    claim = _claim(tmp_path)
    store = AutomationStateStore(tmp_path / "automation.json")
    original = AutomationState(pending_claim=claim)
    store.save(original)
    controller = Controller(status={"state": "recovering", "active": False})
    coordinator = AutomationCoordinator(controller, Admission(tmp_path), store)
    status = coordinator.snapshot(_cycle(0))["automation"]
    assert status["operational"] is False
    assert status["blocked_reason"] == "automation_state_ambiguous"
    assert store.load() == original


def test_pending_claim_with_different_durable_job_is_ambiguous(tmp_path: Path):
    claim = _claim(tmp_path)
    store = AutomationStateStore(tmp_path / "automation.json")
    original = AutomationState(pending_claim=claim)
    store.save(original)
    other = tmp_path / "other.mp4"
    controller = Controller(status={
        "state": "completed", "active": False,
        "source_url": "https://www.tiktok.com/@other/live",
        "output_path": str(other),
        "parts_directory": str(other.with_suffix(".parts")),
    })
    coordinator = AutomationCoordinator(controller, Admission(tmp_path), store)
    assert coordinator.snapshot(_cycle(0))["automation"]["blocked_reason"] == (
        "automation_state_ambiguous"
    )
    assert store.load() == original


def test_corrupt_state_disables_only_automatic_behavior(tmp_path: Path):
    path = tmp_path / "automation.json"
    path.write_text('{"signed_url":"https://secret.invalid/token"}', encoding="utf-8")
    controller = Controller()
    coordinator = AutomationCoordinator(
        controller, Admission(tmp_path), AutomationStateStore(path)
    )
    cycle = _cycle(1, ("creator", "live", "123"))
    coordinator.cycle_completed(cycle)
    status = coordinator.snapshot(cycle)
    assert controller.starts == []
    assert status["automation"]["blocked_reason"] == "automation_state_unavailable"
    assert "secret" not in json.dumps(status)

    # The same controller remains usable through the manual owner path.
    controller.start(
        "https://www.tiktok.com/@manual/live", str(tmp_path / "manual.mp4")
    )
    assert len(controller.starts) == 1
    assert path.read_text(encoding="utf-8").startswith('{"signed_url"')


def test_claim_write_failure_prevents_controller_start(tmp_path: Path):
    store = FailingStore(fail_saves={1})
    controller = Controller()
    coordinator = AutomationCoordinator(controller, Admission(tmp_path), store)
    coordinator.cycle_completed(_cycle(1, ("creator", "live", "123")))
    status = coordinator.snapshot(_cycle(1))["automation"]
    assert controller.starts == []
    assert status["blocked_reason"] == "automation_state_unavailable"


def test_promotion_failure_retains_claim_for_restart_reconciliation(tmp_path: Path):
    store = FailingStore(fail_saves={2})
    controller = Controller()
    coordinator = AutomationCoordinator(controller, Admission(tmp_path), store)
    coordinator.cycle_completed(_cycle(1, ("creator", "live", "123")))
    assert len(controller.starts) == 1
    assert store.state.pending_claim is not None
    assert coordinator.snapshot(_cycle(1))["automation"]["blocked_reason"] == (
        "automation_state_ambiguous"
    )

    restarted = AutomationCoordinator(controller, Admission(tmp_path), store)
    assert store.state.pending_claim is None
    assert store.state.consumed() == {"creator": "123"}
    assert restarted.snapshot(_cycle(1))["automation"]["operational"] is True


def test_rejected_start_clear_failure_retains_ambiguous_claim(tmp_path: Path):
    store = FailingStore(fail_saves={2})
    controller = Controller(failure=RecordingBusy("busy"))
    coordinator = AutomationCoordinator(controller, Admission(tmp_path), store)
    coordinator.cycle_completed(_cycle(1, ("creator", "live", "123")))
    assert store.state.pending_claim is not None
    status = coordinator.snapshot(_cycle(1))["automation"]
    assert status["operational"] is False
    assert status["blocked_reason"] == "automation_state_ambiguous"
