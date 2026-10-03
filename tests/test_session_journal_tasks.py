"""Attempt guards, retained failure pins and exactly-once journal settlement."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from threading import Barrier

import pytest

from tests.session_journal_helpers import capture, intent, journal, proof, queued, rows, uid
from tikrec.session_journal import SessionJournal
from tikrec.session_journal_types import AttemptExitProof, JournalConflict, JournalError


def test_competing_claims_one_running_and_receipt_replay(tmp_path):
    store = journal(tmp_path)
    queued(store, intent("one", "1"))
    queued(store, intent("two", "2"))
    barrier = Barrier(2)
    def claim(_):
        peer = SessionJournal(store.path, store.catalog_id)
        operation, token = uid(), uid()
        barrier.wait(timeout=5)
        result = peer.claim_next(operation, token)
        assert peer.claim_next(operation, token) == result
        return result
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(claim, range(2)))
    assert sum(result is not None for result in results) == 1
    assert sorted(task["state"] for task in store.status()["tasks"]) == ["queued", "running"]


def test_failed_task_keeps_unit_room_artifacts_and_does_not_block_capture(tmp_path):
    store = journal(tmp_path)
    old, _ = queued(store)
    claim = store.claim_next(uid(), uid())
    exit_proof = AttemptExitProof(old.session_id, claim["token"], "owned-child-exited")
    failed = store.fail_task(uid(), old.session_id, claim["revision"], claim["attempt"],
                             claim["token"], exit_proof, "assembly_failed")
    previous = store.session(old.session_id)
    assert previous["task"]["state"] == "failed"
    assert len(previous["artifacts"]) == 2 and previous["rooms"] == ["123"]
    assert len(store.status()["units"]) == 1
    capture(store, intent(room="456", raw=False))
    assert store.session(old.session_id) == previous
    with pytest.raises(JournalConflict):
        store.reserve(uid(), intent("alias", "123"))
    store.retry_failed(uid(), old.session_id, failed["revision"], failed["attempt"],
                       failed["token"], exit_proof)
    second = store.claim_next(uid(), uid())
    assert second["attempt"] == 2 and second["token"] != claim["token"]
    before = rows(store)
    with pytest.raises(JournalConflict):
        store.fail_task(uid(), old.session_id, claim["revision"], 1, claim["token"],
                         exit_proof, "late_callback")
    assert rows(store) == before


def test_old_attempt_token_cannot_be_reused_after_failed_requeue(tmp_path):
    store = journal(tmp_path)
    selected, _ = queued(store)
    claim = store.claim_next(uid(), uid())
    exited = AttemptExitProof(selected.session_id, claim["token"], "owned-exit")
    failed = store.fail_task(uid(), selected.session_id, claim["revision"], 1, claim["token"],
                             exited, "failed")
    store.retry_failed(uid(), selected.session_id, failed["revision"], 1, claim["token"], exited)
    before = rows(store)
    with pytest.raises(JournalConflict):
        store.claim_next(uid(), claim["token"])
    assert rows(store) == before
    second = store.claim_next(uid(), uid())
    assert second["attempt"] == 2
    ledger = rows(store)["attempts"]
    assert len(ledger) == 2 and sorted(x[3] for x in ledger) == ["failed", "running"]


def test_uncertain_child_remains_sole_finalizer_but_new_capture_is_safe(tmp_path):
    store = journal(tmp_path)
    old, _ = queued(store)
    queued(store, intent("other", "456"))
    claim = store.claim_next(uid(), uid())
    held = store.hold_attempt(uid(), old.session_id, claim["revision"], claim["attempt"],
                              claim["token"], "exit_unproven")
    assert held["revision"] == claim["revision"] + 1
    assert store.claim_next(uid(), uid()) is None
    capture(store, intent(room="789"))
    assert len(store.status()["units"]) == 3
    assert store.session(old.session_id)["task"]["error"] == "exit_unproven"


def test_blocked_queue_retains_pins_and_allows_disjoint_capture(tmp_path):
    store = journal(tmp_path)
    old, _ = queued(store)
    store.block_queued(uid(), old.session_id, 1, "unusable_evidence")
    assert store.claim_next(uid(), uid()) is None
    capture(store, intent(room="456"))
    assert len(store.status()["units"]) == 2
    assert store.session(old.session_id)["task"]["state"] == "blocked"
    before = rows(store)
    with pytest.raises(JournalConflict):
        store.block_queued(uid(), old.session_id, 1, "stale")
    assert rows(store) == before


def test_exactly_once_settlement_releases_only_target_unit_and_keeps_history(tmp_path):
    store = journal(tmp_path)
    old, _ = queued(store)
    new, _ = capture(store, intent(room="456", raw=False))
    claim = store.claim_next(uid(), uid())
    selected_proof = proof(store, old, claim)
    operation = uid()
    newer_before = store.session(new.session_id)
    terminal = store.settle_task(operation, old.session_id, claim["revision"], claim["attempt"],
                                 claim["token"], selected_proof)
    assert store.settle_task(operation, old.session_id, claim["revision"], claim["attempt"],
                              claim["token"], selected_proof) == terminal
    assert len(store.status()["units"]) == 1
    assert store.session(new.session_id) == newer_before
    previous = store.session(old.session_id)
    assert previous["task"]["state"] == "completed" and previous["intent"]["raw_copy"] is True
    assert previous["seal"]["artifacts"] and not previous["artifacts"] and not previous["rooms"]
    assert store.automatic_receipt(old.automatic_claim)["session"] == old.session_id
    before = rows(store)
    with pytest.raises(JournalConflict):
        store.settle_task(uid(), old.session_id, claim["revision"], claim["attempt"],
                          claim["token"], selected_proof)
    assert rows(store) == before


def test_competing_settlements_release_one_unit_once(tmp_path):
    store = journal(tmp_path)
    selected, _ = queued(store)
    claim = store.claim_next(uid(), uid())
    selected_proof = proof(store, selected, claim)
    barrier = Barrier(2)
    def settle(_):
        peer = SessionJournal(store.path, store.catalog_id)
        barrier.wait(timeout=5)
        try:
            return peer.settle_task(uid(), selected.session_id, claim["revision"], claim["attempt"],
                                     claim["token"], selected_proof)
        except JournalConflict:
            return None
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(settle, range(2)))
    assert sum(result is not None for result in results) == 1
    assert not store.status()["units"]
    assert store.session(selected.session_id)["task"]["state"] == "completed"


@pytest.mark.parametrize("field,value", [("revision", 99), ("attempt", 99), ("token", "different")])
def test_stale_task_guards_have_zero_side_effects(tmp_path, field, value):
    store = journal(tmp_path)
    old, _ = queued(store)
    claim = store.claim_next(uid(), uid())
    changed = dict(claim)
    changed[field] = uid() if field == "token" else value
    before = rows(store)
    with pytest.raises(JournalConflict):
        store.hold_attempt(uid(), old.session_id, changed["revision"], changed["attempt"],
                            changed["token"], "stale")
    assert rows(store) == before


def test_conflicting_publication_proof_and_operation_reuse_are_refused(tmp_path):
    store = journal(tmp_path)
    old, _ = queued(store)
    claim = store.claim_next(uid(), uid())
    selected = proof(store, old, claim)
    before = rows(store)
    for changed in [replace(selected, seal_hash="a" * 64),
                    replace(selected, output=intent("other", "9").output),
                    replace(selected, session_id=uid()), replace(selected, attempt_token=uid())]:
        with pytest.raises(JournalError):
            store.settle_task(uid(), old.session_id, claim["revision"], claim["attempt"],
                               claim["token"], changed)
        assert rows(store) == before
    operation = uid()
    store.hold_attempt(operation, old.session_id, claim["revision"], claim["attempt"],
                        claim["token"], "first_reason")
    before = rows(store)
    with pytest.raises(JournalConflict):
        store.hold_attempt(operation, old.session_id, claim["revision"], claim["attempt"],
                            claim["token"], "changed_reason")
    assert rows(store) == before
