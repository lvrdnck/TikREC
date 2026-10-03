"""Bounded queries from the isolated internal journal facade."""

import pytest

from tests.session_journal_helpers import intent, journal, queued, uid
from tikrec.session_journal_types import JournalError


def test_bounded_history_and_invalid_arguments(tmp_path):
    store = journal(tmp_path)
    one, _ = queued(store, intent("one", "1"))
    two, _ = queued(store, intent("two", "2"))
    first = store.history(limit=1)
    assert first[0]["id"] == one.session_id
    assert store.history(after=first[0]["seq"], limit=1)[0]["id"] == two.session_id
    for changes in [{"limit": 101}, {"limit": True}, {"after": -1}]:
        with pytest.raises(JournalError):
            store.history(**changes)
    assert store.session(uid()) is None and store.automatic_receipt(uid()) is None
