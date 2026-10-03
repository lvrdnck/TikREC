"""Journal-level ownership tests; production remains synchronous and unwired."""

from dataclasses import replace

import pytest

from tests.session_journal_helpers import capture, closing, intent, journal, queued, rows, seal, uid
from tikrec.session_journal import SessionJournal
from tikrec.session_journal_types import (ArtifactIdentity, JournalConflict, JournalError,
                                        AttemptExitProof, ReservationReleaseProof)


def test_handoff_reuse_keeps_session_receipts_raw_policy_and_old_room(tmp_path):
    store = journal(tmp_path)
    old = intent()
    accepted = store.reserve(uid(), old, slot=1)
    binding = store.admit(uid(), old.session_id, accepted["generation"], 1, "123")
    binding = store.capture_intent(uid(), old.session_id, binding["generation"], 2,
                                   closing=True, stop=True, recovery="user_stop")
    before = store.session(old.session_id)
    handed = store.handoff(uid(), old.session_id, binding["generation"], 3, seal(old, binding))
    newer, current = capture(store, intent(room="456", raw=False), slot=1)
    assert current["generation"] == accepted["generation"] + 1
    previous = store.session(old.session_id)
    assert previous["intent"] == before["intent"]
    assert previous["stop"] == 1 and previous["recovery"] == "user_stop"
    assert previous["seal"]["raw_copy"] is True and len(previous["seal"]["artifacts"]) == 5
    assert previous["rooms"] == ["123"] and len(previous["artifacts"]) == 2
    assert previous["task"]["state"] == "queued"
    assert store.automatic_receipt(old.automatic_claim)["session"] == old.session_id
    assert store.reserve(uid(), old) == accepted  # durable acceptance idempotence after reuse
    assert store.session(newer.session_id)["intent"]["raw_copy"] is False
    assert handed["seal_hash"] == previous["seal_hash"]
    reopened = SessionJournal(store.path, store.catalog_id)
    assert reopened.session(old.session_id) == previous
    before = rows(store)
    for candidate in [intent(room="123"), intent("alias", "123"),
                      replace(intent("other", "789"), output=old.output),
                      replace(intent("other", "789"), parts=old.parts)]:
        with pytest.raises(JournalConflict):
            store.reserve(uid(), candidate)
        assert rows(store) == before


def test_two_tasks_two_new_captures_and_single_finalizer(tmp_path):
    store = journal(tmp_path)
    one, _ = queued(store, intent("one", "1"))
    two, _ = queued(store, intent("two", "2"))
    assert all(b["session"] is None for b in store.status()["bindings"])
    capture(store, intent("one", "3"))
    capture(store, intent("two", "4"))
    assert len(store.status()["units"]) == 4
    assert len(store.status()["tasks"]) == 2
    with pytest.raises(JournalConflict):
        store.reserve(uid(), intent("three", "5"))
    claim = store.claim_next(uid(), uid())
    assert claim["session_id"] == one.session_id
    assert store.claim_next(uid(), uid()) is None
    assert store.session(two.session_id)["task"]["state"] == "queued"


def test_capacity_reservation_transfers_without_extra_unit_at_eight(tmp_path):
    store = journal(tmp_path)
    for number in range(6):
        queued(store, intent(f"creator{number}", str(number + 1)))
    first, first_binding = closing(store, intent("seventh", "7"))
    second, second_binding = closing(store, intent("eighth", "8"))
    assert len(store.status()["units"]) == 8
    for selected, binding in [(first, first_binding), (second, second_binding)]:
        store.handoff(uid(), selected.session_id, binding["generation"], binding["revision"],
                      seal(selected, binding))
        assert len(store.status()["units"]) == 8
    assert len(store.status()["tasks"]) == 8
    before = rows(store)
    with pytest.raises(JournalConflict, match="work limit"):
        store.reserve(uid(), intent("ninth", "9"))
    assert rows(store) == before


def test_failed_work_and_unadmitted_reservations_both_count_at_limit(tmp_path):
    store = journal(tmp_path)
    for number in range(6):
        selected, _ = queued(store, intent(f"old{number}", str(number + 1)))
        claim = store.claim_next(uid(), uid())
        store.fail_task(uid(), selected.session_id, claim["revision"], claim["attempt"], claim["token"],
                         AttemptExitProof(selected.session_id, claim["token"], "exited"), "failed")
    store.reserve(uid(), intent("newone", "7"))
    store.reserve(uid(), intent("newtwo", "8"))
    status = store.status()
    assert len(status["units"]) == 8 and sum(x["kind"] == "capture" for x in status["units"]) == 2
    assert all(x["state"] == "failed" for x in status["tasks"])
    before = rows(store)
    with pytest.raises(JournalConflict, match="work limit"):
        store.reserve(uid(), intent("ninth", "9"))
    assert rows(store) == before


def test_unadmitted_reservation_release_exactly_once(tmp_path):
    store = journal(tmp_path)
    selected = intent()
    accepted = store.reserve(uid(), selected)
    operation = uid()
    release = ReservationReleaseProof(selected.session_id, 1, "proved-no-writer")
    result = store.settle_reservation(operation, selected.session_id, 1, 1, release)
    assert store.settle_reservation(operation, selected.session_id, 1, 1, release) == result
    assert not store.status()["units"] and not store.session(selected.session_id)["artifacts"]
    assert store.automatic_receipt(selected.automatic_claim)["session"] == selected.session_id
    with pytest.raises(JournalConflict):
        store.settle_reservation(uid(), selected.session_id, 1, 1, release)


def test_stale_capture_callbacks_and_mismatched_seal_do_not_touch_reused_slot(tmp_path):
    store = journal(tmp_path)
    old, handed = queued(store)
    capture(store, intent(room="456"))
    before = rows(store)
    for generation, revision in [(handed["generation"], handed["revision"]), (99, 1), (1, 1)]:
        with pytest.raises(JournalConflict):
            store.capture_intent(uid(), old.session_id, generation, revision, stop=True)
        assert rows(store) == before
    new, binding = closing(store, intent("third", "789"))
    before = rows(store)
    for changes in [{"session_id": uid()}, {"generation": 99}, {"room_id": "555"},
                    {"raw_copy": False}, {"ended_at": 50}]:
        original = seal(new, binding)
        if changes == {"raw_copy": False}:
            original = replace(original, artifacts=tuple(a for a in original.artifacts
                                                         if a.role not in {"raw", "arrivals"}))
        with pytest.raises(JournalError):
            store.handoff(uid(), new.session_id, binding["generation"], binding["revision"],
                          replace(original, **changes))
        assert rows(store) == before


def test_unknown_room_page_and_native_subtree_protection(tmp_path):
    store = journal(tmp_path)
    provisional = intent(room=None, automatic=False)
    accepted = store.reserve(uid(), provisional)
    before = rows(store)
    with pytest.raises(JournalConflict):
        store.reserve(uid(), intent(room="555"))
    child = intent("other", "777")
    child = replace(child, output=ArtifactIdentity("volume-1", provisional.parts.components + ("x.mp4",)))
    with pytest.raises(JournalConflict):
        store.reserve(uid(), child)
    assert rows(store) == before
    assert store.admit(uid(), provisional.session_id, accepted["generation"], 1, "555")["revision"] == 2
