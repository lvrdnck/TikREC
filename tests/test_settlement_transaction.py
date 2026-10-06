"""Real file-backed release transaction teardown preserves first errors and lock ownership."""

import sqlite3
from types import SimpleNamespace
from uuid import uuid4

import pytest

from tests.manifest_fence_helpers import ConnectionFaults
from tikrec.settlement_transaction import mutate


@pytest.mark.parametrize('entry', [False, True])
@pytest.mark.parametrize('failures', ['none', 'rollback', 'close', 'both'])
def test_actual_entry_or_body_failure_survives_independent_connection_cleanup(tmp_path, entry, failures):
    path = tmp_path / 'release-reader.sqlite3'
    raw = sqlite3.connect(path, isolation_level=None, timeout=0.05)
    raw.row_factory = sqlite3.Row
    raw.executescript('CREATE TABLE operations(id TEXT,kind TEXT,arguments_hash TEXT,result TEXT); CREATE TABLE facts(value TEXT);')
    primary = sqlite3.OperationalError('first SQLite entry/body failure')
    class Wrapped(ConnectionFaults):
        def execute(self, sql, *args):
            if sql == 'BEGIN IMMEDIATE' and entry:
                raise primary
            return super().execute(sql, *args)
    owner = Wrapped(raw, rollback=OSError('rollback') if failures in {'rollback', 'both'} else None,
        close=OSError('close') if failures in {'close', 'both'} else None)
    journal = SimpleNamespace(_connect=lambda: owner, _audit=lambda _: None, _inject=lambda *_: None)
    readers = []
    def body(db):
        db.execute("INSERT INTO facts VALUES ('must roll back')")
        raise primary
    try:
        with pytest.raises(sqlite3.OperationalError) as error:
            mutate(journal, readers, str(uuid4()), 'prepare_release', [], body)
        assert error.value is primary
        assert owner.calls[-2:] == ['rollback', 'close']
        assert (readers[0].connection is owner) == (failures in {'close', 'both'})
        if failures == 'both' and not entry:
            writer = sqlite3.connect(path, isolation_level=None, timeout=0.05)
            try:
                with pytest.raises(sqlite3.OperationalError, match='locked'):
                    writer.execute("INSERT INTO facts VALUES ('competing writer')")
                owner.rollback_error, owner.close_error = None, None
                assert readers[0].cleanup() == ()
                writer.execute("INSERT INTO facts VALUES ('competing writer')")
                assert writer.execute('SELECT value FROM facts').fetchall() == [('competing writer',)]
            finally:
                writer.close()
    finally:
        raw.close()
