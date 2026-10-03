"""R1: committed stop blocks fresh admission; receipts remain historical evidence."""

import json
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event

import pytest

from tests.session_journal_helpers import intent, journal, rows, uid
from tikrec.session_journal import SessionJournal
from tikrec.session_journal_types import JournalConflict, JournalError, JournalUncertain


@pytest.mark.parametrize("reopen", [False, True])
def test_stop_before_latest_revision_admission_preserves_every_record(tmp_path, reopen):
    store = journal(tmp_path)
    selected = intent()
    accepted = store.reserve(uid(), selected)
    stopped = store.capture_intent(uid(), selected.session_id, accepted["generation"], 1, stop=True)
    peer = SessionJournal(store.path, store.catalog_id) if reopen else store
    before = rows(store)
    operation = uid()
    with pytest.raises(JournalConflict):
        peer.admit(operation, selected.session_id, stopped["generation"], stopped["revision"], "123")
    assert rows(store) == before
    assert peer.operation(operation) is None
    assert peer.session(selected.session_id)["stop"] == 1
    assert peer.automatic_receipt(selected.automatic_claim)["session"] == selected.session_id


def test_historical_reserve_and_admit_receipts_are_not_fresh_writer_permission(tmp_path):
    store = journal(tmp_path)
    selected, reserve_op, admit_op = intent(), uid(), uid()
    accepted = store.reserve(reserve_op, selected)
    admitted = store.admit(admit_op, selected.session_id, accepted["generation"], 1, "123")
    store.capture_intent(uid(), selected.session_id, accepted["generation"], 2, stop=True)
    before = rows(store)
    assert store.reserve(reserve_op, selected) == accepted
    assert store.admit(admit_op, selected.session_id, accepted["generation"], 1, "123") == admitted
    assert json.loads(store.operation(admit_op)["result"]) == admitted
    assert store.session(selected.session_id)["stop"] == 1
    with pytest.raises(JournalConflict):
        store.admit(uid(), selected.session_id, accepted["generation"], 3, "123")
    assert rows(store) == before


@pytest.mark.parametrize("boundary", ["before_commit", "after_commit"])
def test_uncertain_stop_ack_is_reconciled_before_refreshed_admission(tmp_path, boundary):
    store = journal(tmp_path)
    selected, stop_op = intent(), uid()
    accepted = store.reserve(uid(), selected)
    def fault(kind, point):
        if (kind, point) == ("capture_intent", boundary):
            raise OSError("lost acknowledgement or pre-commit failure")
    peer = SessionJournal(store.path, store.catalog_id, fault=fault)
    with pytest.raises(JournalUncertain if boundary == "after_commit" else JournalError):
        peer.capture_intent(stop_op, selected.session_id, accepted["generation"], 1, stop=True)
    reopened = SessionJournal(store.path, store.catalog_id)
    assert (reopened.operation(stop_op) is not None) == (boundary == "after_commit")
    stopped = reopened.capture_intent(stop_op, selected.session_id, accepted["generation"], 1, stop=True)
    before = rows(reopened)
    with pytest.raises(JournalConflict):
        reopened.admit(uid(), selected.session_id, stopped["generation"], stopped["revision"], "123")
    assert rows(reopened) == before


def test_competing_stop_and_admit_have_one_guarded_winner(tmp_path):
    store = journal(tmp_path)
    selected = intent()
    accepted = store.reserve(uid(), selected)
    barrier = Barrier(2)
    def compete(kind):
        peer = SessionJournal(store.path, store.catalog_id)
        barrier.wait(timeout=5)
        try:
            if kind == "stop":
                result = peer.capture_intent(uid(), selected.session_id, accepted["generation"], 1, stop=True)
            else:
                result = peer.admit(uid(), selected.session_id, accepted["generation"], 1, "123")
            return kind, result
        except JournalConflict:
            return kind, None
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(compete, ["stop", "admit"]))
    assert sum(result is not None for _, result in results) == 1
    current = store.session(selected.session_id)
    if current["stop"] == 0:
        store.capture_intent(uid(), selected.session_id, accepted["generation"], current["revision"], stop=True)
    latest = store.session(selected.session_id)
    before = rows(store)
    with pytest.raises(JournalConflict):
        store.admit(uid(), selected.session_id, accepted["generation"], latest["revision"], "123")
    assert rows(store) == before


@pytest.mark.parametrize("first", ["stop", "admit"])
def test_both_serialized_stop_admission_orders_with_real_lock_contention(tmp_path, first):
    store = journal(tmp_path)
    selected = intent()
    accepted = store.reserve(uid(), selected)
    locked, release, contender_started = Event(), Event(), Event()
    first_operation = uid()
    first_kind = "capture_intent" if first == "stop" else "admit"
    def fault(kind, boundary):
        if (kind, boundary) == (first_kind, "before_commit"):
            locked.set()
            assert release.wait(timeout=5)
    winner = SessionJournal(store.path, store.catalog_id, fault=fault)
    contender = SessionJournal(store.path, store.catalog_id)
    def invoke(peer, kind, operation):
        if kind == "stop":
            return peer.capture_intent(operation, selected.session_id, accepted["generation"], 1, stop=True)
        return peer.admit(operation, selected.session_id, accepted["generation"], 1, "123")
    def second():
        contender_started.set()
        with pytest.raises(JournalConflict):
            invoke(contender, "admit" if first == "stop" else "stop", uid())
    with ThreadPoolExecutor(max_workers=2) as executor:
        pending = executor.submit(invoke, winner, first, first_operation)
        try:
            assert locked.wait(timeout=5)
            competing = executor.submit(second)
            assert contender_started.wait(timeout=5)
        finally:
            release.set()
        assert pending.result(timeout=5)["revision"] == 2
        competing.result(timeout=5)
    current = store.session(selected.session_id)
    assert (current["stop"], current["phase"]) == ((1, "reserved") if first == "stop" else (0, "capturing"))
    if first == "admit":
        store.capture_intent(uid(), selected.session_id, accepted["generation"], 2, stop=True)
        assert store.admit(first_operation, selected.session_id, accepted["generation"], 1, "123")["revision"] == 2
    before = rows(store)
    with pytest.raises(JournalConflict):
        store.admit(uid(), selected.session_id, accepted["generation"],
                    store.session(selected.session_id)["revision"], "123")
    assert rows(store) == before


@pytest.mark.parametrize("boundary", ["before_commit", "after_commit"])
def test_admission_ack_then_stop_distinguishes_replay_from_permission(tmp_path, boundary):
    store = journal(tmp_path)
    selected, operation = intent(), uid()
    store.reserve(uid(), selected)
    def fault(kind, point):
        if (kind, point) == ("admit", boundary):
            raise OSError("admission acknowledgement failure")
    peer = SessionJournal(store.path, store.catalog_id, fault=fault)
    with pytest.raises(JournalUncertain if boundary == "after_commit" else JournalError):
        peer.admit(operation, selected.session_id, 1, 1, "123")
    reopened = SessionJournal(store.path, store.catalog_id)
    committed = reopened.operation(operation)
    assert (committed is not None) == (boundary == "after_commit")
    current = reopened.session(selected.session_id)
    stopped = reopened.capture_intent(uid(), selected.session_id, 1, current["revision"], stop=True)
    before = rows(reopened)
    if committed is not None:
        assert reopened.admit(operation, selected.session_id, 1, 1, "123") == json.loads(committed["result"])
    else:
        with pytest.raises(JournalConflict):
            reopened.admit(operation, selected.session_id, 1, 1, "123")
    with pytest.raises(JournalConflict):
        reopened.admit(uid(), selected.session_id, 1, stopped["revision"], "123")
    assert rows(reopened) == before
