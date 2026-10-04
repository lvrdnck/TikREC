"""FIFO, competing claims, immutable inputs and capture capacity stay independent."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import os
import pytest

from tests.capture_handoff_helpers import observations, reserve
from tests.sealed_input_helpers import sealed
from tests.test_attempt_coordinator_faults import execute, factory
from tests.owned_process_helpers import managed_process
from tikrec.attempt_coordinator import AttemptCoordinator, AttemptError
from tikrec.session_journal_types import JournalError


pytestmark = pytest.mark.skipif(os.name != "nt", reason="real Windows capture and native input proof")


def test_competing_fifo_claims_and_two_disjoint_capture_slots(sealed):
    owner, first, _ = sealed
    data = (owner.root.parent / "source.flv").read_bytes()
    second = reserve(owner, "two", room="234", creator="creator2")
    assert second.run(**observations(data, room="234")).phase == "queued"
    contenders = [AttemptCoordinator(owner), AttemptCoordinator(owner)]
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            claims = list(pool.map(lambda runner: runner.claim(), contenders))
        winners = [claim for claim in claims if claim is not None]
        assert len(winners) == 1 and winners[0]["session_id"] == first.intent.session_id
        replacements = [reserve(owner, "capture3", room="345", creator="creator3"),
                        reserve(owner, "capture4", room="456", creator="creator4")]
        status = owner.journal.status()
        assert len(status["units"]) == 4 and sum(b["session"] is not None for b in status["bindings"]) == 2
        for bridge, room in zip(replacements, ("345", "456"), strict=True):
            assert bridge.run(**observations(data, room=room)).phase == "queued"
        assert len(owner.journal.status()["units"]) == 4
    finally:
        for runner in contenders:
            assert runner.close()


def test_added_evidence_blocks_creation_without_repair(sealed, managed_process):
    owner, bridge, _ = sealed
    runner = AttemptCoordinator(owner, process_factory=factory(managed_process))
    runner.claim()
    added = Path(bridge.intent.parts_path) / "unexpected.txt"
    added.write_text("retain")
    try:
        with pytest.raises(AttemptError):
            execute(runner)
        assert not runner.children and added.read_text() == "retain"
        assert owner.journal.owned_attempt(runner.token)["sequence"] == 0
    finally:
        assert runner.close()


def test_external_revocation_before_resume_is_durable_and_irreversible(sealed, managed_process):
    owner, _, _ = sealed
    payload = owner.root.parent / "payload.txt"
    def revoke(point):
        if point == "after_identity":
            owner.journal.revoke_owned(runner.uuid(), runner.token, runner.owner, runner.revision)
    runner = AttemptCoordinator(owner, process_factory=factory(managed_process), fault=revoke)
    runner.claim()
    try:
        with pytest.raises(AttemptError):
            execute(runner, "from pathlib import Path;Path(" + repr(str(payload)) + ").touch()")
        assert not payload.exists()
        assert owner.journal.owned_attempt(runner.token)["state"] == "revoked"
        assert runner.children[0]["process"].closed
        with pytest.raises(JournalError):
            owner.journal.launch_intent(runner.uuid(), runner.token, runner.owner,
                runner.revision, runner.uuid(), {"executable": "C:\\python.exe", "arguments": [],
                    "cwd": str(owner.root), "phase": "probe", "seal_hash": runner.guard.seal_hash,
                    "marker_hash": runner.guard.revalidate().marker_sha256, "predecessor": None})
    finally:
        runner._fault = lambda _: None
        assert runner.close()


def test_added_evidence_after_identity_blocks_resume(sealed, managed_process):
    owner, bridge, _ = sealed
    payload = owner.root.parent / "payload.txt"
    added = Path(bridge.intent.parts_path) / "added-after-identity.txt"
    def change(point):
        if point == "after_identity":
            added.write_text("preserve")
    runner = AttemptCoordinator(owner, process_factory=factory(managed_process), fault=change)
    runner.claim()
    try:
        with pytest.raises(AttemptError):
            execute(runner, "from pathlib import Path;Path(" + repr(str(payload)) + ").touch()")
        assert not payload.exists() and added.read_text() == "preserve"
        child = owner.journal.owned_attempt(runner.token)["child"]
        assert child["identity"] is not None and child["cleanup"] == 0
        # Revalidation also refuses to advance exit bookkeeping after namespace
        # tampering. Native owners are still closed independently and reachable.
        assert runner.children[0]["process"].closed
    finally:
        runner._fault = lambda _: None
        assert runner.close()
