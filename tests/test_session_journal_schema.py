"""Actual file-backed schema constraints protect immutable journal history."""

import sqlite3

import pytest

from tests.session_journal_helpers import journal, queued, rows


def test_immutable_identity_raw_seal_and_receipts_protected_by_schema(tmp_path):
    store = journal(tmp_path)
    selected, _ = queued(store)
    before = rows(store)
    with sqlite3.connect(store.path) as connection:
        for sql in ["UPDATE sessions SET intent='{}'", "UPDATE sessions SET creator='other'",
                    "UPDATE sessions SET room='999'", "UPDATE sessions SET generation=99",
                    "UPDATE sessions SET seal='{}'", "DELETE FROM sessions",
                    "UPDATE automatic_receipts SET intent_hash='wrong'", "DELETE FROM automatic_receipts",
                    "UPDATE operations SET result='{}'", "DELETE FROM operations"]:
            with pytest.raises(sqlite3.IntegrityError):
                connection.execute(sql)
    assert rows(store) == before
    assert store.automatic_receipt(selected.automatic_claim) is not None
