"""R3: durable queue-entry FIFO rather than capture-acceptance order."""

import pytest
import json
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from tests.session_journal_helpers import closing, intent, journal, queued, rows, seal, uid
from tikrec.session_journal import SessionJournal
from tikrec.session_journal_types import AttemptExitProof, JournalError, JournalUncertain


def test_reverse_acceptance_handoff_claims_first_queue_entry_after_reopen(tmp_path):
    store = journal(tmp_path)
    first, first_binding = closing(store, intent("first", "1"))
    second, second_binding = closing(store, intent("second", "2"))
    for selected, binding in [(second, second_binding), (first, first_binding)]:
        store.handoff(uid(), selected.session_id, binding["generation"], binding["revision"], seal(selected, binding))
    reopened = SessionJournal(store.path, store.catalog_id)
    assert reopened.claim_next(uid(), uid())["session_id"] == second.session_id


def test_failed_retry_moves_to_tail_once_and_replay_keeps_place(tmp_path):
    store = journal(tmp_path)
    old, _ = queued(store, intent("old", "1"))
    claim = store.claim_next(uid(), uid())
    exit_proof = AttemptExitProof(old.session_id, claim["token"], "owned-exit")
    failed = store.fail_task(uid(), old.session_id, claim["revision"], claim["attempt"],
                             claim["token"], exit_proof, "assembly_failed")
    newer, _ = queued(store, intent("newer", "2"))
    operation = uid()
    retried = store.retry_failed(operation, old.session_id, failed["revision"], failed["attempt"],
                                failed["token"], exit_proof)
    before = rows(store)
    assert store.retry_failed(operation, old.session_id, failed["revision"], failed["attempt"],
                              failed["token"], exit_proof) == retried
    assert rows(store) == before
    reopened = SessionJournal(store.path, store.catalog_id)
    assert reopened.claim_next(uid(), uid())["session_id"] == newer.session_id


def fifo_operation(store, kind):
    """Prepare competing queue history outside a handoff/retry fault boundary."""
    if kind == "handoff":
        selected, binding = closing(store, intent("earlier", "1"))
        earlier_queue, _ = queued(store, intent("later", "2"))
        operation = uid()
        invoke = lambda peer: peer.handoff(operation, selected.session_id, binding["generation"],
                                           binding["revision"], seal(selected, binding))
    else:
        selected, _ = queued(store, intent("earlier", "1"))
        claim = store.claim_next(uid(), uid())
        proof = AttemptExitProof(selected.session_id, claim["token"], "owned-exit")
        failed = store.fail_task(uid(), selected.session_id, claim["revision"], claim["attempt"],
                                 claim["token"], proof, "assembly_failed")
        earlier_queue, _ = queued(store, intent("later", "2"))
        operation = uid()
        invoke = lambda peer: peer.retry_failed(operation, selected.session_id, failed["revision"],
                                                failed["attempt"], failed["token"], proof)
    return operation, selected, earlier_queue, invoke


@pytest.mark.parametrize("kind", ["handoff", "retry_failed"])
@pytest.mark.parametrize("boundary", ["after_begin", "after_queue_entry", "after_task", "after_writes",
                                     "before_commit", "after_commit"])
def test_fifo_entry_rollback_lost_ack_and_replay_have_one_position(tmp_path, kind, boundary):
    store = journal(tmp_path)
    operation, selected, earlier_queue, invoke = fifo_operation(store, kind)
    before = rows(store)
    def fault(actual, point):
        if (actual, point) == (kind, boundary):
            raise OSError("queue ordering failure")
    peer = SessionJournal(store.path, store.catalog_id, fault=fault)
    with pytest.raises(JournalUncertain if boundary == "after_commit" else JournalError):
        invoke(peer)
    reopened = SessionJournal(store.path, store.catalog_id)
    receipt = reopened.operation(operation)
    if boundary == "after_commit":
        assert receipt is not None
        committed = rows(store)
        assert invoke(reopened) == json.loads(receipt["result"])
        assert rows(store) == committed
    else:
        assert receipt is None and rows(store) == before
        invoke(reopened)
    place = reopened.session(selected.session_id)["task"]["queue_order"]
    assert place > reopened.session(earlier_queue.session_id)["task"]["queue_order"]
    committed = rows(store)
    invoke(reopened)
    assert rows(store) == committed
    assert reopened.claim_next(uid(), uid())["session_id"] == earlier_queue.session_id


def test_competing_claims_select_the_committed_fifo_head_once(tmp_path):
    store = journal(tmp_path)
    first, binding = closing(store, intent("first", "1"))
    head, _ = queued(store, intent("second", "2"))
    store.handoff(uid(), first.session_id, binding["generation"], binding["revision"], seal(first, binding))
    barrier = Barrier(2)
    def claim(_):
        peer = SessionJournal(store.path, store.catalog_id)
        barrier.wait(timeout=5)
        return peer.claim_next(uid(), uid())
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(claim, range(2)))
    winners = [x for x in results if x is not None]
    assert len(winners) == 1 and winners[0]["session_id"] == head.session_id
