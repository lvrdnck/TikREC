"""Unsupported reviewed catalogues stay intact; there is no silent migration."""

import sqlite3
from types import SimpleNamespace

import pytest

from tests.session_journal_helpers import intent, uid
from tests.session_journal_review_helpers import seed_reserved
from tests.session_journal_v1_fixture import SCHEMA_V1
from tests.session_journal_v3_fixture import SCHEMA_V3
from tests.session_journal_v4_fixture import SCHEMA_V4
from tests.session_journal_v5_fixture import SCHEMA as SCHEMA_V5
from tikrec.session_journal import SessionJournal
from tikrec.session_journal_schema import APPLICATION_ID, SCHEMA_VERSION
from tikrec.session_journal_types import JournalError


def test_schema_six_and_old_version_one_refusal(tmp_path):
    assert SCHEMA_VERSION == 6
    path, catalog = tmp_path / "old-reviewed.sqlite3", uid()
    with sqlite3.connect(path) as connection:
        connection.executescript(SCHEMA_V1)
        connection.execute(f"PRAGMA application_id={APPLICATION_ID}")
        connection.execute("PRAGMA user_version=1")
        connection.execute("INSERT INTO catalog VALUES (?,1)", (catalog,))
        connection.executemany("INSERT INTO bindings VALUES (?,0,NULL)", [(1,), (2,)])
    seed_reserved(SimpleNamespace(path=path), intent(), 1)
    before = path.read_bytes()
    with pytest.raises(JournalError, match="schema"):
        SessionJournal(path, catalog)
    with pytest.raises(FileExistsError):
        SessionJournal.initialize(path, catalog)
    assert path.read_bytes() == before
    with sqlite3.connect(path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 1
        assert connection.execute("SELECT version FROM catalog").fetchone()[0] == 1
        assert connection.execute("SELECT count(*) FROM sessions").fetchone()[0] == 1
        assert "queue_entries" not in [x[0] for x in connection.execute("SELECT name FROM sqlite_master")]


def test_retained_schema_five_is_refused_byte_for_byte(tmp_path):
    path, catalog = tmp_path / "accepted-five.sqlite3", uid()
    with sqlite3.connect(path) as connection:
        connection.executescript(SCHEMA_V5)
        connection.execute(f"PRAGMA application_id={APPLICATION_ID}")
        connection.execute("PRAGMA user_version=5")
        connection.execute("INSERT INTO catalog VALUES (?,5)", (catalog,))
        connection.executemany("INSERT INTO bindings VALUES (?,0,NULL)", [(1,), (2,)])
    seed_reserved(SimpleNamespace(path=path), intent(), 1)
    before = path.read_bytes()
    with pytest.raises(JournalError, match="schema"):
        SessionJournal(path, catalog)
    with pytest.raises(FileExistsError):
        SessionJournal.initialize(path, catalog)
    assert path.read_bytes() == before
    with sqlite3.connect(path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 5
        assert connection.execute("SELECT version FROM catalog").fetchone()[0] == 5
        assert connection.execute("SELECT count(*) FROM sessions").fetchone()[0] == 1
        assert "candidate_validations" not in [x[0] for x in connection.execute("SELECT name FROM sqlite_master")]


def test_retained_schema_four_is_refused_byte_for_byte(tmp_path):
    path, catalog = tmp_path / "accepted-four.sqlite3", uid()
    with sqlite3.connect(path) as connection:
        connection.executescript(SCHEMA_V4)
        connection.execute(f"PRAGMA application_id={APPLICATION_ID}")
        connection.execute("PRAGMA user_version=4")
        connection.execute("INSERT INTO catalog VALUES (?,4)", (catalog,))
        connection.executemany("INSERT INTO bindings VALUES (?,0,NULL)", [(1,), (2,)])
    seed_reserved(SimpleNamespace(path=path), intent(), 1)
    before = path.read_bytes()
    with pytest.raises(JournalError, match="schema"):
        SessionJournal(path, catalog)
    with pytest.raises(FileExistsError):
        SessionJournal.initialize(path, catalog)
    assert path.read_bytes() == before
    with sqlite3.connect(path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 4
        assert connection.execute("SELECT version FROM catalog").fetchone()[0] == 4
        assert connection.execute("SELECT count(*) FROM sessions").fetchone()[0] == 1
        names = [row[0] for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")]
        assert "scratch_owners" not in names
def test_retained_schema_three_is_refused_without_migration(tmp_path):
    path, catalog = tmp_path / "accepted-three.sqlite3", uid()
    with sqlite3.connect(path) as connection:
        connection.executescript(SCHEMA_V3)
        connection.execute(f"PRAGMA application_id={APPLICATION_ID}")
        connection.execute("PRAGMA user_version=3")
        connection.execute("INSERT INTO catalog VALUES (?,3)", (catalog,))
        connection.executemany("INSERT INTO bindings VALUES (?,0,NULL)", [(1,), (2,)])
    seed_reserved(SimpleNamespace(path=path), intent(), 1)
    before = path.read_bytes()
    with pytest.raises(JournalError, match="schema"):
        SessionJournal(path, catalog)
    with pytest.raises(FileExistsError):
        SessionJournal.initialize(path, catalog)
    assert path.read_bytes() == before
