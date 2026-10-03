"""R2: automatic provenance must bind receipt, session and immutable intent."""

import pytest
import sqlite3
from dataclasses import asdict

from tests.session_journal_helpers import intent, journal, rows, uid
from tests.session_journal_review_helpers import seed_reserved
from tikrec.session_journal import SessionJournal
from tikrec.session_journal_types import JournalError, digest, encode


@pytest.mark.parametrize("receipt", ["missing", "wrong_hash", "wrong_session"])
def test_required_outstanding_receipt_binding_refused_without_side_effects(tmp_path, receipt):
    store = journal(tmp_path)
    manual = intent("manual", "777", automatic=False)
    seed_reserved(store, manual, 1)
    selected = intent("automatic", "123")
    seed_reserved(store, selected, 2, receipt=receipt,
                  receipt_session=manual.session_id if receipt == "wrong_session" else None)
    before = rows(store)
    with pytest.raises(JournalError):
        SessionJournal(store.path, store.catalog_id)
    with pytest.raises(JournalError):
        store.status()
    with pytest.raises(JournalError):
        store.automatic_receipt(selected.automatic_claim)
    with pytest.raises(JournalError):
        store.claim_next(uid(), uid())
    assert rows(store) == before


@pytest.mark.parametrize("receipt", ["missing", "wrong_hash"])
def test_addressed_historical_receipt_validated_without_scanning_history(tmp_path, receipt):
    store = journal(tmp_path)
    selected = intent()
    seed_reserved(store, selected, 1, terminal=True, receipt=receipt)
    # Unrelated history is not scanned by reopen/status; the addressed claim is checked.
    reopened = SessionJournal(store.path, store.catalog_id)
    assert not reopened.status()["units"]
    before = rows(store)
    with pytest.raises(JournalError):
        reopened.automatic_receipt(selected.automatic_claim)
    with pytest.raises(JournalError):
        reopened.reserve(uid(), selected)
    assert rows(store) == before


def test_absent_unknown_claim_is_not_accepted_provenance(tmp_path):
    store = journal(tmp_path)
    assert store.automatic_receipt(uid()) is None


@pytest.mark.parametrize("receipt", ["missing", "wrong_hash"])
def test_historical_operation_replay_checks_addressed_automatic_binding(tmp_path, receipt):
    store = journal(tmp_path)
    selected, operation = intent(), uid()
    seed_reserved(store, selected, 1, terminal=True, receipt=receipt)
    result = {"session_id": selected.session_id, "slot": 1, "generation": 1, "revision": 1}
    with sqlite3.connect(store.path) as connection:
        connection.execute("INSERT INTO operations VALUES (?,'reserve',?,?)",
                           (operation, digest({"intent": asdict(selected), "slot": None}), encode(result)))
    reopened = SessionJournal(store.path, store.catalog_id)
    before = rows(store)
    for address in [lambda: reopened.operation(operation), lambda: reopened.reserve(operation, selected),
                    lambda: reopened.session(selected.session_id)]:
        with pytest.raises(JournalError):
            address()
        assert rows(store) == before
