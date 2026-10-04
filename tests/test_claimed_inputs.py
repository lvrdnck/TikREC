"""Claimed protection inherits strict evidence mechanics without rewriting H."""

import os
from pathlib import Path

import pytest

from tests.sealed_input_helpers import sealed
from tikrec.attempt_coordinator import AttemptCoordinator, AttemptError
from tikrec.sealed_input_native import ReadProtection

pytestmark = pytest.mark.skipif(os.name != "nt", reason="Windows claimed read protection")


@pytest.mark.parametrize("boundary", ["after_lifecycle", "after_open_1", "after_open_4", "after_inventory"])
def test_acquisition_failure_preserves_committed_claim_and_reachable_guard(sealed, boundary):
    owner, _, _ = sealed
    def fault(point):
        if point == boundary:
            raise ValueError("input acquisition failed")
    runner = AttemptCoordinator(owner, fault=fault)
    with pytest.raises(AttemptError) as failure:
        runner.claim()
    assert failure.value.coordinator is runner
    assert runner.guard is not None and runner.guard.closed
    assert owner.journal.owned_attempt(runner.token)["state"] == "held"
    assert owner.journal.owned_attempt(runner.token)["marker_hash"] is None
    assert len(owner.journal.status()["units"]) == 1
    assert runner.close()


def test_claimed_guard_close_failure_keeps_exact_handle_reachable(sealed, monkeypatch):
    owner, _, _ = sealed
    runner = AttemptCoordinator(owner)
    runner.claim()
    held = runner.guard.files[0]
    original = ReadProtection.close
    def fail(value):
        if value is held:
            raise OSError("claimed file release failed")
        original(value)
    monkeypatch.setattr(ReadProtection, "close", fail)
    assert not runner.close()
    assert held in runner.guard.retained and held.handle is not None
    with pytest.raises(OSError):
        held.path.open("ab")
    monkeypatch.setattr(ReadProtection, "close", original)
    assert runner.close() and held.handle is None


def test_changed_control_before_claim_refuses_without_repair(sealed):
    owner, bridge, _ = sealed
    control = Path(bridge.intent.parts_path) / "session.json"
    original = control.read_bytes()
    control.write_bytes(original + b" ")
    runner = AttemptCoordinator(owner)
    with pytest.raises(AttemptError):
        runner.claim()
    assert control.read_bytes() == original + b" " and not runner.children
    assert owner.journal.owned_attempt(runner.token)["state"] == "held"
    assert runner.close()
