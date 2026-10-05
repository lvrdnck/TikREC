"""Scratch cleanup failures and lost durable acknowledgements remain auditable."""

import os
import sys
from pathlib import Path

import pytest

from tests.owned_process_helpers import managed_process
from tests.sealed_input_helpers import sealed
from tikrec.attempt_coordinator import AttemptCoordinator


pytestmark = pytest.mark.skipif(os.name != "nt", reason="native scratch ownership requires Windows")


def process_factory(make):
    """Retain independent exact-job cleanup for every contained child."""
    def create(session_id, token):
        child = make()
        child.session_id, child.attempt_token = session_id, token
        return child
    return create


def test_candidate_owner_close_failure_remains_reachable(sealed, managed_process):
    owner, _, _ = sealed
    runner = AttemptCoordinator(owner, process_factory=process_factory(managed_process))
    runner.claim()
    scratch = runner.reserve_scratch()
    scratch.run_writer(Path(sys._base_executable), ["-c",
        "from pathlib import Path;Path('candidate.mp4').write_bytes(b'candidate')"], timeout=10)
    scratch.seal_candidate(runner.children[-1]["launch"])
    original_api, handle = scratch.workspace.api, scratch.workspace.handle

    class FailedClose:
        """Model an unconfirmed native directory-handle close without losing its value."""
        @staticmethod
        def CloseHandle(_handle):
            return 0
    try:
        scratch.workspace.api = FailedClose()
        assert not runner.close()
        assert scratch.workspace.handle == handle
        assert runner.errors
        assert owner.journal.scratch(runner.token)["candidate"]["publication"] == "unpublished"
    finally:
        scratch.workspace.api = original_api
        assert runner.close()


@pytest.mark.parametrize("kind", ["reserve_scratch", "bind_scratch",
                                   "bind_scratch_artifacts", "seal_candidate"])
def test_lost_scratch_receipts_reconcile_same_filesystem_work(sealed, managed_process, kind):
    owner, _, _ = sealed
    runner = AttemptCoordinator(owner, process_factory=process_factory(managed_process))
    fired = []
    def lose_ack(selected, boundary):
        if selected == kind and boundary == "after_commit" and not fired:
            fired.append(selected)
            raise OSError("lost scratch acknowledgement")
    owner.journal._fault = lose_ack
    try:
        runner.claim()
        scratch = runner.reserve_scratch()
        scratch.run_writer(Path(sys._base_executable), ["-c",
            "from pathlib import Path;Path('candidate.mp4').write_bytes(b'candidate')"], timeout=10)
        record = scratch.seal_candidate(runner.children[-1]["launch"])
        assert record["publication"] == "unpublished"
        assert fired == [kind] and runner.errors
        assert len(owner.journal.child_history(runner.token)) == 1
        assert owner.journal.owned_attempt(runner.token)["scratch"]["state"] == "candidate_ready"
    finally:
        owner.journal._fault = None
        runner.close()
