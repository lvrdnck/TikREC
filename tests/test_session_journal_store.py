"""Fail-closed authority, settings, lock contention and immutable stored records."""

import sqlite3
import os
import time
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest

from tests.session_journal_helpers import capture, intent, journal, queued, rows, uid
from tikrec.session_journal import SessionJournal
from tikrec.session_journal_types import JournalBusy, JournalConflict, JournalError, JournalUncertain


def test_explicit_fresh_and_reopen_verify_actual_settings(tmp_path):
    store = journal(tmp_path)
    checks = store.diagnostics()
    assert checks["sqlite_version"] == sqlite3.sqlite_version
    assert checks["source_id"] and checks["journal_mode"] == "delete"
    assert checks["synchronous"] == 3 and checks["foreign_keys"] == 1
    assert checks["busy_timeout"] == 1000
    assert store.status()["bindings"] == [{"slot": 1, "generation": 0, "session": None},
                                           {"slot": 2, "generation": 0, "session": None}]
    before = store.path.read_bytes()
    with pytest.raises(FileExistsError):
        SessionJournal.initialize(store.path, uid())
    assert store.path.read_bytes() == before
    assert SessionJournal(store.path, store.catalog_id).diagnostics() == checks


def test_missing_state_or_parent_never_creates_replacement(tmp_path):
    missing = tmp_path / "absent" / "sessions.sqlite3"
    with pytest.raises(JournalError):
        SessionJournal(missing, uid())
    with pytest.raises(JournalError):
        SessionJournal.initialize(missing, uid())
    assert not missing.parent.exists()
    store = journal(tmp_path)
    preserved = store.path.with_suffix(".preserved")
    store.path.rename(preserved)
    with pytest.raises(JournalError):
        store.reserve(uid(), intent())
    assert not store.path.exists() and preserved.exists()


@pytest.mark.parametrize("failure", ["corrupt", "identity", "schema_version", "application_id",
                                     "extra_schema", "wrong_mode", "missing_binding"])
def test_invalid_catalog_rejected_without_mutation_or_recreation(tmp_path, failure):
    store = journal(tmp_path)
    capture(store)
    if failure == "corrupt":
        store.path.write_bytes(b"not a SQLite database; preserve this evidence")
    elif failure != "identity":
        with sqlite3.connect(store.path) as connection:
            statement = {"schema_version": "PRAGMA user_version=99",
                         "application_id": "PRAGMA application_id=99",
                         "extra_schema": "CREATE TABLE unsupported(extra TEXT)",
                         "wrong_mode": "PRAGMA journal_mode=WAL",
                         "missing_binding": "DELETE FROM bindings WHERE slot=2"}[failure]
            connection.execute(statement)
    before = store.path.read_bytes()
    with pytest.raises(JournalError):
        SessionJournal(store.path, uid() if failure == "identity" else store.catalog_id)
    assert store.path.read_bytes() == before
    assert store.path.exists()
    if failure == "wrong_mode":
        with sqlite3.connect(store.path) as connection:
            assert connection.execute("PRAGMA journal_mode").fetchone()[0] == "wal"


def test_replaced_file_refused_by_existing_instance(tmp_path):
    store = journal(tmp_path)
    store.path.rename(tmp_path / "old.sqlite3")
    replacement = SessionJournal.initialize(store.path, store.catalog_id)
    before = rows(replacement)
    with pytest.raises(JournalError, match="replaced"):
        store.reserve(uid(), intent())
    assert rows(replacement) == before


def test_multiply_linked_catalog_refused_without_removing_evidence(tmp_path):
    store = journal(tmp_path)
    alias = tmp_path / "alias.sqlite3"
    os.link(store.path, alias)
    before = store.path.read_bytes()
    with pytest.raises(JournalError):
        SessionJournal(store.path, store.catalog_id)
    assert alias.read_bytes() == store.path.read_bytes() == before


def test_exclusive_contention_is_bounded_transient_and_no_side_effects(tmp_path):
    store = journal(tmp_path)
    before = rows(store)
    blocker = sqlite3.connect(store.path, isolation_level=None)
    try:
        blocker.execute("BEGIN EXCLUSIVE")
        started = time.monotonic()
        with pytest.raises(JournalBusy):
            store.reserve(uid(), intent())
        assert 0.7 <= time.monotonic() - started < 5
    finally:
        blocker.rollback()
        blocker.close()
    assert rows(store) == before
    assert store.reserve(uid(), intent())["revision"] == 1


def test_reader_blocks_commit_timeout_is_uncertain_until_receipt_lookup(tmp_path):
    store = journal(tmp_path)
    before = rows(store)
    reader = sqlite3.connect(store.path, isolation_level=None)
    operation, selected = uid(), intent()
    try:
        reader.execute("BEGIN")
        reader.execute("SELECT * FROM bindings").fetchall()
        with pytest.raises(JournalUncertain):
            store.reserve(operation, selected)
    finally:
        reader.rollback()
        reader.close()
    reopened = SessionJournal(store.path, store.catalog_id)
    assert reopened.operation(operation) is None  # observed absence, not assumed rollback
    assert rows(reopened) == before
    accepted = reopened.reserve(operation, selected)
    assert reopened.reserve(operation, selected) == accepted


@pytest.mark.parametrize("same_artifact", [False, True])
def test_competing_acceptances_keep_one_authoritative_owner(tmp_path, same_artifact):
    store = journal(tmp_path)
    first = intent("one", "123", name="same" if same_artifact else None)
    second = intent("two", "456" if same_artifact else "123", name="same" if same_artifact else None)
    barrier = Barrier(2)
    def reserve(selected):
        peer = SessionJournal(store.path, store.catalog_id)
        barrier.wait(timeout=5)
        try:
            return peer.reserve(uid(), selected)
        except JournalConflict:
            return None
    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(reserve, [first, second]))
    assert sum(value is not None for value in outcomes) == 1
    assert len(store.history()) == 1 and len(store.status()["units"]) == 1
    assert sum(store.automatic_receipt(x.automatic_claim) is not None for x in [first, second]) == 1
