"""R11: preserve first exceptions, independent close and exact reader ownership."""

import sqlite3
from threading import Thread

import pytest

from tests.manifest_fence_helpers import reader_fixture


@pytest.mark.parametrize('where', ['entry', 'guard', 'body', 'success'])
@pytest.mark.parametrize('rollback,close', [(False, False), (True, False), (False, True), (True, True)])
def test_actual_fence_preserves_first_failure_and_separate_cleanup(tmp_path, monkeypatch, where, rollback, close):
    primary = OSError('first entry/body failure')
    rollback_error, close_error = sqlite3.OperationalError('rollback fault'), sqlite3.OperationalError('close fault')
    faults = {'entry': primary if where == 'entry' else None,
              'rollback': rollback_error if rollback else None, 'close': close_error if close else None}
    with reader_fixture(tmp_path, monkeypatch, **faults) as (fence, wrapped, _):
        if where == 'guard':
            def refuse(*_args, **_kwargs):
                raise primary
            monkeypatch.setattr('tikrec.session_journal_manifest.owner_guard', refuse)
        expected = primary if where != 'success' else rollback_error if rollback else close_error if close else None
        observed = None
        try:
            with fence():
                if where == 'body':
                    raise primary
        except BaseException as error:
            observed = error
        assert observed is expected
        assert wrapped.calls[-2:] == ['rollback', 'close']
        if rollback or close:
            owner = observed.manifest_fence_owner
            assert owner.errors == ([('rollback', rollback_error)] if rollback else []) + ([('close', close_error)] if close else [])
            assert owner.connection is (wrapped if close else None)
            assert owner.evidence()['cleanup_complete'] is (not close)
            assert owner.evidence()['connection_retained'] is close
            wrapped.rollback_error = wrapped.close_error = None
            owner.cleanup()
            assert owner.connection is None and owner.evidence()['cleanup_complete']


@pytest.mark.parametrize('failed_close', [False, True])
def test_file_backed_reader_close_allows_exact_pending_writer_commit(tmp_path, monkeypatch, failed_close):
    primary, rollback_error = OSError('first guarded failure'), sqlite3.OperationalError('rollback unavailable')
    close_error = sqlite3.OperationalError('close unavailable') if failed_close else None
    with reader_fixture(tmp_path, monkeypatch, rollback=rollback_error, close=close_error) as (fence, wrapped, path):
        observed = None
        try:
            with fence():
                assert wrapped.raw.in_transaction
                raise primary
        except BaseException as error:
            observed = error
        writer = sqlite3.connect(path, isolation_level=None, timeout=0.05)
        try:
            writer.execute('BEGIN IMMEDIATE')
            writer.execute("INSERT INTO disjoint VALUES ('once')")
            busy = None
            try:
                writer.commit()
            except sqlite3.OperationalError as error:
                busy = error
            assert observed is primary
            assert wrapped.calls[-2:] == ['rollback', 'close']
            owner = observed.manifest_fence_owner
            if failed_close:
                assert busy is not None and 'locked' in str(busy) and writer.in_transaction
                assert owner.connection is wrapped and wrapped.raw.in_transaction
                wrapped.rollback_error = wrapped.close_error = None
                assert owner.cleanup() == ()
                writer.commit()  # Commit the same INSERT; never reissue it.
            else:
                assert busy is None and owner.connection is None
            assert writer.execute('SELECT value FROM disjoint').fetchall() == [('once',)]
        finally:
            writer.close()


def test_failed_close_after_native_close_still_retains_until_confirmation(tmp_path, monkeypatch):
    close_error = sqlite3.OperationalError('close return unknown')
    with reader_fixture(tmp_path, monkeypatch, close=close_error, close_after=True) as (fence, wrapped, _):
        with pytest.raises(sqlite3.OperationalError) as caught:
            with fence():
                pass
        owner = caught.value.manifest_fence_owner
        assert caught.value is close_error and owner.connection is wrapped
        wrapped.close_error = None
        owner.cleanup()
        assert owner.evidence()['cleanup_complete'] and owner.connection is None


def test_repeated_exact_cleanup_is_one_attempt_and_diagnostics_are_bounded(tmp_path, monkeypatch):
    primary = KeyboardInterrupt('first interrupt')
    with reader_fixture(tmp_path, monkeypatch, rollback=OSError('rollback'), close=OSError('close')) as (fence, wrapped, _):
        with pytest.raises(KeyboardInterrupt) as caught:
            with fence():
                raise primary
        owner = caught.value.manifest_fence_owner
        assert caught.value is primary
        for _ in range(40):
            before = len(wrapped.calls)
            owner.cleanup()
            assert wrapped.calls[before:] == ['rollback', 'close']
        assert len(owner.errors) == 32 and owner.errors_dropped == 50
        assert owner.connection is wrapped and not owner.evidence()['cleanup_complete']


def test_wrong_thread_cleanup_keeps_exact_connection_until_owning_thread_confirms(tmp_path, monkeypatch):
    with reader_fixture(tmp_path, monkeypatch, close=OSError('close unknown')) as (fence, wrapped, _):
        with pytest.raises(OSError) as caught:
            with fence():
                pass
        owner = caught.value.manifest_fence_owner
        wrapped.close_error = None
        results = []
        worker = Thread(target=lambda: results.append(owner.cleanup()))
        worker.start()
        worker.join(5)
        assert not worker.is_alive() and len(results[0]) == 2
        assert all(isinstance(error, sqlite3.ProgrammingError) for _, error in results[0])
        assert owner.connection is wrapped and not owner.evidence()['cleanup_complete']
        assert owner.cleanup() == () and owner.connection is None
