"""Exact real SQLite connections with independently injectable teardown faults."""

import json
import sqlite3
from contextlib import contextmanager
from types import SimpleNamespace

from tikrec.session_journal_manifest import ManifestOperations
from tikrec.session_journal_types import digest


class ConnectionFaults:
    """Keep the real reader reachable even when an injected native result is unknown."""

    def __init__(self, connection, *, entry=None, rollback=None, close=None, close_after=False):
        self.raw = connection
        self.entry_error, self.rollback_error, self.close_error = entry, rollback, close
        self.close_after, self.calls = close_after, []

    def execute(self, sql, *args):
        self.calls.append('execute:' + sql)
        if sql == 'BEGIN' and self.entry_error is not None:
            raise self.entry_error
        return self.raw.execute(sql, *args)

    def rollback(self):
        self.calls.append('rollback')
        if self.rollback_error is not None:
            raise self.rollback_error
        return self.raw.rollback()

    def close(self):
        self.calls.append('close')
        if self.close_after:
            self.raw.close()
        if self.close_error is not None:
            raise self.close_error
        return self.raw.close()


@contextmanager
def reader_fixture(tmp_path, monkeypatch, **faults):
    """Call the repository fence; only its owner checker is isolated in this matrix."""
    from tikrec import session_journal_manifest as module
    path = tmp_path / 'reader.sqlite3'
    connection = sqlite3.connect(path, isolation_level=None, timeout=0.05)
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA journal_mode=DELETE')
    connection.executescript('''
        CREATE TABLE manifest_preparations(token TEXT, operation TEXT, binding TEXT);
        CREATE TABLE manifest_steps(token TEXT, phase TEXT, evidence TEXT, operation TEXT);
        CREATE TABLE disjoint(value TEXT);
    ''')
    connection.execute('INSERT INTO manifest_preparations VALUES (?,?,?)', ('token', 'prepare', json.dumps({})))
    wrapped = ConnectionFaults(connection, **faults)
    store = SimpleNamespace(_connect=lambda: wrapped)
    monkeypatch.setattr(module, 'owner_guard', lambda *_args, **_kwargs: None)
    fence = lambda: ManifestOperations.manifest_fence(store, 'token', 'owner', 1, 'prepare', digest({}), 0)
    try:
        yield fence, wrapped, path
    finally:
        # Independent disposable cleanup must also run when the baseline fails.
        connection.close()


def inject_selected_fence(journal, monkeypatch, count, **faults):
    """Wrap only the exact native-fence connection, leaving all other journal I/O real."""
    original, connect, retained = journal.manifest_fence, journal._connect, []

    @contextmanager
    def selected(*args):
        if args[-1] == count and not retained:
            def once():
                monkeypatch.setattr(journal, '_connect', connect)
                wrapped = ConnectionFaults(connect(), **faults)
                retained.append(wrapped)
                return wrapped
            monkeypatch.setattr(journal, '_connect', once)
        with original(*args):
            yield

    monkeypatch.setattr(journal, 'manifest_fence', selected)
    return retained
