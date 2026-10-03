"""Real rollback/commit receipts and bounded subprocess death, not power-loss tests."""

import json
import subprocess
import sys

import pytest

from tests.session_journal_helpers import capture, closing, intent, journal, proof, queued, rows, seal, uid
from tikrec.session_journal import SessionJournal
from tikrec.session_journal_types import JournalUncertain


BOUNDARIES = {
    "reserve": ["after_begin", "after_session", "after_binding", "after_unit", "after_claims",
                "after_receipt", "after_writes", "before_commit", "after_commit"],
    "handoff": ["after_begin", "after_seal", "after_queue_entry", "after_task", "after_transfer", "after_release",
                "after_writes", "before_commit", "after_commit"],
    "settle_task": ["after_begin", "after_terminal", "after_unit_release", "after_claim_release",
                    "after_writes", "before_commit", "after_commit"],
}


def operation_fixture(store, kind):
    """Prepare operation arguments outside the faulting transaction."""
    operation = uid()
    if kind == "reserve":
        selected = intent()
        return operation, selected, lambda peer: peer.reserve(operation, selected)
    if kind == "handoff":
        selected, binding = closing(store)
        selected_seal = seal(selected, binding)
        return operation, selected, lambda peer: peer.handoff(
            operation, selected.session_id, binding["generation"], binding["revision"], selected_seal)
    selected, _ = queued(store)
    claim = store.claim_next(uid(), uid())
    selected_proof = proof(store, selected, claim)
    return operation, selected, lambda peer: peer.settle_task(
        operation, selected.session_id, claim["revision"], claim["attempt"], claim["token"], selected_proof)


@pytest.mark.parametrize("kind,boundary", [(kind, boundary) for kind, points in BOUNDARIES.items()
                                          for boundary in points])
def test_failure_every_transaction_boundary_reopens_and_reconciles(tmp_path, kind, boundary):
    store = journal(tmp_path)
    unrelated, _ = capture(store, intent("unrelated", "999"))
    unrelated_before = store.session(unrelated.session_id)
    operation, selected, invoke = operation_fixture(store, kind)
    before = rows(store)
    def fault(actual, point):
        if (actual, point) == (kind, boundary):
            raise OSError("injected acknowledgement or write failure")
    peer = SessionJournal(store.path, store.catalog_id, fault=fault)
    with pytest.raises(JournalUncertain if boundary == "after_commit" else ValueError):
        invoke(peer)
    reopened = SessionJournal(store.path, store.catalog_id)
    if boundary == "after_commit":
        receipt = reopened.operation(operation)
        assert receipt is not None
        durable = rows(reopened)
        assert invoke(reopened) == json.loads(receipt["result"])
        assert rows(reopened) == durable
    else:
        assert reopened.operation(operation) is None
        assert rows(reopened) == before
        invoke(reopened)
    receipt = reopened.operation(operation)
    assert receipt is not None
    assert reopened.session(unrelated.session_id) == unrelated_before
    if kind == "reserve":
        assert reopened.automatic_receipt(selected.automatic_claim)["session"] == selected.session_id
    if kind == "handoff":
        assert reopened.session(selected.session_id)["task"]["state"] == "queued"
    if kind == "settle_task":
        assert reopened.session(selected.session_id)["task"]["state"] == "completed"


CHILD = r'''
import json, os, sys
from dataclasses import asdict
from pathlib import Path
from tests.test_session_journal_faults import operation_fixture
from tikrec.session_journal import SessionJournal
path, catalog, kind, boundary, record_path = sys.argv[1:]
store = SessionJournal(Path(path), catalog)
operation, selected, invoke = operation_fixture(store, kind)
Path(record_path).write_text(json.dumps({'operation': operation, 'intent': asdict(selected),
                                      'prepared': store.session(selected.session_id)}))
def fault(actual, point):
    if (actual, point) == (kind, boundary): os._exit(91)
store._fault = fault
# Force dirty pages out before COMMIT to exercise actual rollback-journal recovery.
original_connect = store._connect
def connect():
    connection = original_connect()
    connection.execute('PRAGMA cache_size=1')
    return connection
store._connect = connect
invoke(store)
'''


@pytest.mark.parametrize("kind", ["reserve", "handoff", "settle_task"])
@pytest.mark.parametrize("boundary", ["after_writes", "before_commit", "after_commit"])
def test_process_death_around_commit_has_one_durable_outcome(tmp_path, kind, boundary):
    store = journal(tmp_path)
    unrelated, _ = capture(store, intent("unrelated", "999"))
    unrelated_before = store.session(unrelated.session_id)
    record_path = tmp_path / "child-operation.json"
    child = subprocess.run([sys.executable, "-c", CHILD, str(store.path), store.catalog_id,
                            kind, boundary, str(record_path)],
                           capture_output=True, text=True, timeout=15)
    assert child.returncode == 91, child.stderr
    record = json.loads(record_path.read_text())
    assert store.path.with_name(store.path.name + "-journal").exists() == (boundary != "after_commit")
    reopened = SessionJournal(store.path, store.catalog_id)
    receipt = reopened.operation(record["operation"])
    assert (receipt is not None) == (boundary == "after_commit")
    assert reopened.session(unrelated.session_id) == unrelated_before
    session = reopened.session(record["intent"]["session_id"])
    if kind == "reserve":
        assert (session is not None) == (boundary == "after_commit")
        assert (reopened.automatic_receipt(record["intent"]["automatic_claim"]) is not None) == (
            boundary == "after_commit")
    elif kind == "handoff":
        assert session["phase"] == ("queued" if boundary == "after_commit" else "closing")
        assert (session["task"] is not None) == (boundary == "after_commit")
    else:
        assert session["phase"] == ("completed" if boundary == "after_commit" else "running")
    assert len(reopened.status()["units"]) == (
        1 if kind == "reserve" and boundary != "after_commit" or
        kind == "settle_task" and boundary == "after_commit" else 2)
    # Reconstruct the SAME operation after inspecting its durable receipt/state.
    from tikrec.session_journal_capture import intent_from_record
    selected = intent_from_record(json.dumps(record["intent"]))
    operation = record["operation"]
    if kind == "reserve":
        result = reopened.reserve(operation, selected)
    elif kind == "handoff":
        prepared = record["prepared"]
        result = reopened.handoff(operation, selected.session_id, prepared["generation"],
                                   prepared["revision"], seal(selected, prepared))
    else:
        claim = record["prepared"]["task"]
        result = reopened.settle_task(operation, selected.session_id, claim["revision"],
                                       claim["attempt"], claim["token"], proof(reopened, selected, claim))
    assert result == json.loads(reopened.operation(operation)["result"])
    assert reopened.session(unrelated.session_id) == unrelated_before
