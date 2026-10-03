"""R2: reject mutually contradictory outstanding owners without selecting a winner."""

from dataclasses import replace

import pytest

from tests.session_journal_helpers import capture, intent, journal, queued, rows, uid
from tests.session_journal_review_helpers import seed_reserved
from tikrec.session_journal import SessionJournal
from tikrec.session_journal_types import ArtifactIdentity, JournalError


@pytest.mark.parametrize("conflict", ["creator", "subtree"])
def test_cross_session_corruption_refused_on_reopen_status_mutation(tmp_path, conflict):
    store = journal(tmp_path)
    unrelated, _ = queued(store, intent("unrelated", "999"))
    first = intent("one", "1")
    second = intent("one" if conflict == "creator" else "two", "2")
    if conflict == "subtree":
        second = replace(second, output=ArtifactIdentity(first.parts.volume,
                                                        first.parts.components + ("nested.mp4",)))
    seed_reserved(store, first, 1)
    seed_reserved(store, second, 2)
    before = rows(store)
    bytes_before = store.path.read_bytes()
    with pytest.raises(JournalError):
        SessionJournal(store.path, store.catalog_id)
    with pytest.raises(JournalError):
        store.status()
    with pytest.raises(JournalError):
        store.claim_next(uid(), uid())
    assert rows(store) == before and store.path.read_bytes() == bytes_before
    assert store.session(unrelated.session_id)["intent"]["creator"] == "unrelated"


def test_same_creator_distinct_room_task_and_capture_is_still_valid(tmp_path):
    store = journal(tmp_path)
    old, _ = queued(store, intent(room="1"))
    new = intent(room="2", raw=False)
    capture(store, new)
    reopened = SessionJournal(store.path, store.catalog_id)
    assert len(reopened.status()["units"]) == 2
    assert reopened.session(old.session_id)["intent"]["raw_copy"] is True
    assert reopened.session(new.session_id)["intent"]["raw_copy"] is False
