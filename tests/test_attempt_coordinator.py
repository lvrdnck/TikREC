"""Durable authority around real H inputs and disposable read-only children."""

import os
import sys
from pathlib import Path

import pytest

from tests.sealed_input_helpers import sealed, hashes
from tests.owned_process_helpers import managed_process


pytestmark = pytest.mark.skipif(os.name != "nt", reason="real Windows capture and native input proof")


def test_sequential_readers_keep_task_and_original_h(sealed, managed_process):
    from tikrec.attempt_coordinator import AttemptCoordinator
    owner, bridge, original = sealed
    before = hashes(owner.root)
    def factory(sid, token):
        child = managed_process()
        child.session_id, child.attempt_token = sid, token
        return child
    runner = AttemptCoordinator(owner, process_factory=factory)
    claim = runner.claim()
    assert claim["session_id"] == bridge.intent.session_id
    assert owner.journal.claim_next(runner.uuid(), runner.uuid()) is None
    for number in (1, 2):
        result = runner.run_child(Path(sys._base_executable),
            ["-c", "import sys;sys.stdout.buffer.write(b'final-tail')"],
            cwd=owner.root, phase="probe", timeout=10)
        assert result.state == "confirmed_exited"
        assert result.stdout == b"final-tail"
        record = owner.journal.owned_attempt(claim["token"])
        assert record["sequence"] == number
        assert record["child"]["exit"] is not None and record["child"]["cleanup"] == 1
    runner.close()
    row = owner.journal.session(bridge.intent.session_id)
    assert row["phase"] == "running" and row["seal_hash"] == original["seal_hash"]
    assert hashes(owner.root) == before
    assert len(owner.journal.status()["units"]) == 1
    assert len(row["artifacts"]) == 2


def test_claimed_guard_does_not_relax_queued_guard(sealed, managed_process):
    from tikrec.attempt_coordinator import AttemptCoordinator
    from tests.sealed_input_helpers import acquire
    from tikrec.sealed_inputs import SealedInputError
    owner, _, _ = sealed
    runner = AttemptCoordinator(owner)
    try:
        runner.claim()
        assert runner.guard.revalidate().revision == runner.revision
        with pytest.raises(SealedInputError):
            acquire(sealed)
    finally:
        runner.close()


def test_closed_runner_and_receipts_are_not_launch_permission(sealed):
    from tikrec.attempt_coordinator import AttemptCoordinator
    owner, _, _ = sealed
    runner = AttemptCoordinator(owner)
    runner.claim()
    runner.close()
    with pytest.raises(Exception):
        runner.run_child(Path(sys._base_executable), ["-c", "pass"],
                         cwd=owner.root, phase="probe", timeout=5)
    replacement = AttemptCoordinator(owner)
    assert replacement.claim() is None
    replacement.close()
