"""Acknowledgement loss, stale records and retained owners on real disposable H."""

import os
import sys
from dataclasses import asdict
from pathlib import Path

import pytest

from tests.sealed_input_helpers import sealed, hashes
from tests.owned_process_helpers import managed_process
from tikrec.attempt_coordinator import AttemptCoordinator, AttemptError
from tikrec.session_journal import SessionJournal
from tikrec.session_journal_types import AttemptExitProof, JournalError


pytestmark = pytest.mark.skipif(os.name != "nt", reason="real Windows capture and native input proof")


def factory(make):
    """Keep independent exact-job cleanup around coordinator-owned native children."""
    def create(sid, token):
        child = make()
        child.session_id, child.attempt_token = sid, token
        return child
    return create


def execute(runner, code="print('tail')"):
    """Run a bounded disposable reader without consuming or publishing media."""
    return runner.run_child(Path(sys._base_executable), ["-c", code],
                            cwd=runner.authority.root, phase="probe", timeout=10)


@pytest.mark.parametrize("kind", ["claim_owned", "bind_owned_inputs", "launch_intent",
                                 "child_identity", "child_exit", "child_diagnostics", "child_cleanup"])
def test_lost_ack_reconciles_once_without_duplicate_creation(sealed, managed_process, kind):
    owner, _, _ = sealed
    runner = AttemptCoordinator(owner, process_factory=factory(managed_process))
    fired = []
    def fault(selected, boundary):
        if selected == kind and boundary == "after_commit" and not fired:
            fired.append(True)
            raise OSError("lost acknowledgement")
    owner.journal._fault = fault
    try:
        runner.claim()
        assert execute(runner).state == "confirmed_exited"
        assert len(runner.children) == 1
        assert len(owner.journal.child_history(runner.token)) == 1
        assert fired and runner.errors
    finally:
        owner.journal._fault = None
        runner.close()


@pytest.mark.parametrize("kind", ["claim_owned", "launch_intent", "child_identity", "child_exit"])
def test_unavailable_reconciliation_refuses_execution_or_successor(sealed, managed_process, monkeypatch, kind):
    owner, _, _ = sealed
    before = hashes(owner.root)
    runner = AttemptCoordinator(owner, process_factory=factory(managed_process))
    fired = []
    def fault(selected, boundary):
        if selected == kind and boundary == "after_commit" and not fired:
            fired.append(True)
            raise OSError("lost acknowledgement")
    def unavailable(_):
        raise JournalError("lookup unavailable")
    owner.journal._fault = fault
    monkeypatch.setattr(owner.journal, "operation", unavailable)
    try:
        with pytest.raises(AttemptError):
            runner.claim()
            execute(runner, "raise SystemExit(0)")
        with pytest.raises(AttemptError):
            execute(runner)
        reopened = SessionJournal(owner.journal.path, owner.journal.catalog_id)
        assert reopened.owned_attempt(runner.token)["state"] == "held"
        assert reopened.status()["tasks"][0]["state"] == "running"
        assert len(reopened.child_history(runner.token)) <= 1
        assert hashes(owner.root) == before
    finally:
        owner.journal._fault = None
        monkeypatch.undo()
        runner.close()


def test_legacy_callbacks_cannot_release_owned_attempt(sealed):
    owner, bridge, _ = sealed
    runner = AttemptCoordinator(owner)
    try:
        claim = runner.claim()
        proof = AttemptExitProof(bridge.intent.session_id, runner.token, "caller_assertion")
        with pytest.raises(JournalError):
            owner.journal.fail_task(runner.uuid(), claim["session_id"], claim["task_revision"],
                                    claim["attempt"], runner.token, proof, "failed")
        assert len(owner.journal.status()["units"]) == 1
    finally:
        runner.close()


def test_repeated_authorization_and_identity_conflict_fail_closed(sealed, managed_process):
    owner, _, _ = sealed
    runner = AttemptCoordinator(owner, process_factory=factory(managed_process))
    try:
        runner.claim()
        execute(runner)
        child = runner.children[0]
        before = owner.journal.path.read_bytes()
        with pytest.raises(JournalError):
            runner._authorize(child, child["process"].identity)
        with pytest.raises(JournalError):
            runner._record(child, "identity", {**asdict(child["process"].identity), "pid": 999})
        assert owner.journal.path.read_bytes() == before
    finally:
        runner.close()
