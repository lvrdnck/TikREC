"""Reopen catches cross-table contradictions beyond SQLite page integrity."""

import sqlite3

import pytest

from tests.session_journal_helpers import capture, journal, queued, uid
from tikrec.session_journal import SessionJournal
from tikrec.session_journal_types import JournalError


@pytest.mark.parametrize("change", ["room", "artifact", "unit", "phase", "binding"])
def test_inconsistent_capture_claims_refused_and_preserved(tmp_path, change):
    store = journal(tmp_path)
    capture(store)
    with sqlite3.connect(store.path) as connection:
        connection.execute({"room": "DELETE FROM rooms",
                            "artifact": "UPDATE artifacts SET identity='{}' WHERE kind='parts'",
                            "unit": "DELETE FROM units",
                            "phase": "UPDATE sessions SET phase='queued'",
                            "binding": "UPDATE bindings SET generation=99 WHERE session IS NOT NULL"}[change])
    before = store.path.read_bytes()
    with pytest.raises(JournalError):
        SessionJournal(store.path, store.catalog_id)
    assert store.path.read_bytes() == before


@pytest.mark.parametrize("change", ["task_state", "task_unit", "attempt", "proof_digest"])
def test_inconsistent_task_claims_refused_and_preserved(tmp_path, change):
    store = journal(tmp_path)
    queued(store)
    claim = store.claim_next(uid(), uid())
    with sqlite3.connect(store.path) as connection:
        if change == "task_state":
            connection.execute("UPDATE tasks SET state='failed'")
        elif change == "task_unit":
            connection.execute("UPDATE units SET kind='capture'")
        elif change == "attempt":
            connection.execute("UPDATE attempts SET state='failed'")
        else:
            # Mutating seal_hash is itself prohibited; assert that SQLite refuses it.
            with pytest.raises(sqlite3.IntegrityError):
                connection.execute("UPDATE sessions SET seal_hash='wrong'")
            return
    before = store.path.read_bytes()
    with pytest.raises(JournalError):
        SessionJournal(store.path, store.catalog_id)
    assert store.path.read_bytes() == before
