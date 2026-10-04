"""Empty closure frees bindings without losing admitted evidence or old authority."""

import sqlite3
from dataclasses import replace
from types import SimpleNamespace

import pytest

from tests.session_journal_helpers import closing, intent, journal, seal, uid
from tests.session_journal_review_helpers import seed_reserved
from tests.session_journal_v2_fixture import SCHEMA_V2
from tikrec.session_journal import SessionJournal
from tikrec.session_journal_schema import APPLICATION_ID
from tikrec.session_journal_types import JournalError


def test_proved_empty_has_no_task_but_keeps_history_claims_and_counted_evidence(tmp_path):
    store = journal(tmp_path)
    selected, binding = closing(store, intent(raw=False))
    ordinary = seal(selected, binding)
    empty = replace(ordinary, artifacts=tuple(a for a in ordinary.artifacts if a.role != "flv"),
                    disposition="empty")
    operation = uid()
    receipt = store.settle_empty_capture(operation, selected.session_id, 1, 3, empty)
    assert store.settle_empty_capture(operation, selected.session_id, 1, 3, empty) == receipt
    status = store.status()
    assert all(b["session"] is None for b in status["bindings"])
    assert status["units"] == [{"session": selected.session_id, "kind": "evidence"}]
    old = store.session(selected.session_id)
    assert old["task"] is None and len(old["artifacts"]) == 2 and old["rooms"] == ["123"]
    assert old["seal"]["disposition"] == "empty"
    store.reserve(uid(), intent(room="456"))
    assert SessionJournal(store.path, store.catalog_id).session(selected.session_id) == old


def test_empty_evidence_audit_uses_bounded_index_instead_of_terminal_history(tmp_path):
    store = journal(tmp_path)
    with sqlite3.connect(store.path) as connection:
        plan = connection.execute(
            "EXPLAIN QUERY PLAN SELECT 1 FROM sessions s LEFT JOIN units u ON u.session=s.id "
            "WHERE s.phase='no_assembly' AND s.seal IS NOT NULL "
            "AND (u.kind IS NULL OR u.kind!='evidence') LIMIT 1").fetchall()
    details = " ".join(row[3] for row in plan)
    assert "sealed_empty_sessions" in details
    assert "SCAN s" not in details or "USING INDEX sealed_empty_sessions" in details


def test_ambiguous_empty_refused_and_schema2_preserved_without_migration(tmp_path):
    store = journal(tmp_path)
    selected, binding = closing(store, intent(raw=False))
    store.capture_intent(uid(), selected.session_id, 1, 3, recovery="ambiguous_state")
    empty = replace(seal(selected, binding), artifacts=tuple(
        a for a in seal(selected, binding).artifacts if a.role != "flv"), disposition="empty")
    with pytest.raises(JournalError):
        store.settle_empty_capture(uid(), selected.session_id, 1, 4, empty)
    path = tmp_path / "old.sqlite3"
    catalog = uid()
    with sqlite3.connect(path) as connection:
        connection.executescript(SCHEMA_V2)
        connection.execute(f"PRAGMA application_id={APPLICATION_ID}")
        connection.execute("PRAGMA user_version=2")
        connection.execute("INSERT INTO catalog VALUES (?,2)", (catalog,))
        connection.executemany("INSERT INTO bindings VALUES (?,0,NULL)", [(1,), (2,)])
    seed_reserved(SimpleNamespace(path=path), intent(), 1)
    before = path.read_bytes()
    with pytest.raises(JournalError, match="schema"):
        SessionJournal(path, catalog)
    with pytest.raises(FileExistsError):
        SessionJournal.initialize(path, uid())
    assert path.read_bytes() == before
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT count(*) FROM sessions").fetchone()[0] == 1
