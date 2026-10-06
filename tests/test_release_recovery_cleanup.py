"""R12: exact failures and possibly-live resources survive recovery faults."""

import os
import sqlite3
from threading import Thread

import pytest

from tests.capture_handoff_helpers import authority
from tests.journal_assembly_helpers import managed_process
from tests.journal_recovery_helpers import prepared_success
from tests.journal_settlement_helpers import independent_cleanup
from tests.test_journal_settlement_cleanup import inject_transaction
from tikrec.capture_handoff_native import NativeHandle
from tikrec.session_journal_types import JournalError


@pytest.fixture
def recovery_case(tmp_path, managed_process, monkeypatch):
    """Keep exact native fixture cleanup independent of product assertions."""
    owner = authority(tmp_path)
    case = prepared_success(owner, tmp_path, managed_process)
    try:
        yield owner, case
    finally:
        monkeypatch.undo()
        owner.journal._fault = None
        for retained in list(owner._recovery_owners.values()):
            for reader in retained.readers:
                connection = reader.connection
                if connection is not None and hasattr(connection, 'close_error'):
                    connection.rollback_error = connection.close_error = None
            if hasattr(retained, 'close'):
                retained.close()
            else:
                retained._close_resources()
                for reader in retained.readers:
                    reader.cleanup()
        independent_cleanup(case['adapter'])
        owner.close()


@pytest.mark.parametrize('available', [False, True])
@pytest.mark.parametrize('kind', ['begin_release_recovery', 'record_release_recovery_proof',
                                 'record_release_recovery_cleanup', 'settle_release_recovery'])
def test_lost_acknowledgement_retains_exact_primary_and_lookup_failure(recovery_case, monkeypatch, available, kind):
    owner, case = recovery_case
    first, secondary = OSError('lost operation acknowledgement'), OSError('lookup unavailable')
    lost = []
    lookup = owner.journal.operation
    def fault(selected, point):
        if selected == kind and point == 'after_commit':
            lost.append(True)
            raise first
    def operation(identity):
        if not available and lost:
            raise secondary
        return lookup(identity)
    owner.journal._fault = fault
    monkeypatch.setattr(owner.journal, 'operation', operation)
    if available:
        assert owner.recover_prepared_release(case['session'], case['token'])['state'] == 'released'
    else:
        with pytest.raises(OSError) as raised:
            owner.recover_prepared_release(case['session'], case['token'])
        assert raised.value is first and secondary in first.recovery_secondary_errors
    terminal = available or kind == 'settle_release_recovery'
    assert owner.journal.settlement(case['token'])['state'] == ('released' if terminal else 'cleanup_confirmed')
    assert len(owner.journal.status()['units']) == (0 if terminal else 1)
    owner.journal._fault = None
    monkeypatch.setattr(owner.journal, 'operation', lookup)
    assert owner.recover_prepared_release(case['session'], case['token'])['state'] == 'released'
    assert owner.journal.release_recovery(case['token'])['head']['generation'] == (1 if terminal else 2)
    assert owner.journal.settlement(case['token'])['preparation'] == case['record']['preparation']
    assert owner.journal.settlement(case['token'])['cleanup'] == case['record']['cleanup']
    assert owner.journal.status()['units'] == []


@pytest.mark.parametrize('after', [False, True])
def test_native_cleanup_raises_the_exact_first_error(recovery_case, monkeypatch, after):
    owner, case = recovery_case
    first, second = OSError('first native cleanup'), OSError('second native cleanup')
    close, observed = NativeHandle.close, []
    output = case['bridge'].intent.output_path
    def failed(held):
        if str(held.path) == output:
            observed.append(first)
            if after:
                close(held)
            raise first
        if held.path.name == 'session.json':
            observed.append(second)
            close(held)
            raise second
        return close(held)
    monkeypatch.setattr(NativeHandle, 'close', failed)
    with pytest.raises(BaseException) as raised:
        owner.recover_prepared_release(case['session'], case['token'])
    # Resource-list order determines which cleanup error happened first.
    assert raised.value is observed[0]
    assert first in raised.value.recovery_errors and second in raised.value.recovery_errors
    assert raised.value.recovery_owner.journal is owner.journal
    assert owner.journal.release_recovery(case['token'])['cleanup']['evidence']['cleanup_complete'] is False
    assert len(owner.journal.status()['units']) == 1


@pytest.mark.parametrize('kind', ['begin_release_recovery', 'record_release_recovery_proof',
                                'record_release_recovery_cleanup', 'settle_release_recovery'])
@pytest.mark.parametrize('faults', ['rollback', 'close', 'both'])
def test_sqlite_cleanup_preserves_exact_errors_connections_and_commits(recovery_case, monkeypatch, kind, faults):
    owner, case = recovery_case
    rollback, close = sqlite3.OperationalError('rollback'), sqlite3.OperationalError('close')
    wrapped = inject_transaction(owner.journal, monkeypatch, kind,
        rollback=rollback if faults != 'close' else None, close=close if faults != 'rollback' else None)
    with pytest.raises(BaseException) as raised:
        owner.recover_prepared_release(case['session'], case['token'])
    assert raised.value is (rollback if faults != 'close' else close)
    recovery = raised.value.recovery_owner
    assert all(error in raised.value.recovery_errors for error in
               ([rollback, close] if faults == 'both' else [raised.value]))
    reader = next(r for r in recovery.readers if r.errors)
    terminal = kind == 'settle_release_recovery'
    assert owner.journal.settlement(case['token'])['state'] == ('released' if terminal else 'cleanup_confirmed')
    assert len(owner.journal.status()['units']) == (0 if terminal else 1)
    if faults != 'rollback':
        assert owner._recovery_owners[case['token']] is recovery
        with pytest.raises(JournalError):
            owner.close()
        wrapped[0].rollback_error = wrapped[0].close_error = None
        wrong = []
        worker = Thread(target=lambda: wrong.append(recovery.close()))
        worker.start()
        worker.join(5)
        assert not worker.is_alive() and wrong == [False]
        assert reader.connection is wrapped[0]
        assert any(isinstance(e, sqlite3.ProgrammingError) for _, e in reader.errors)
        assert recovery.close() and reader.connection is None
    if terminal:
        assert owner.recover_prepared_release(case['session'], case['token'])['state'] == 'released'


@pytest.mark.parametrize('attachment', ['handle', 'descriptor'])
def test_real_partial_lifecycle_acquisition_is_registered_before_generation(
        recovery_case, monkeypatch, attachment):
    from tikrec import lifecycle_lock as lifecycle
    owner, case = recovery_case
    primary, secondary = OSError('lease acquisition failed'), OSError('lease cleanup failed')
    open_lock, identity, raw_close = lifecycle._open_lock, lifecycle._identity, os.close
    retained, confirmed = [], False
    class FailedFile:
        def __init__(self, raw):
            self.raw = raw
        def __getattr__(self, name):
            return getattr(self.raw, name)
        def close(self):
            raise secondary
    if attachment == 'handle':
        def opened(*args, **kwargs):
            held = FailedFile(open_lock(*args, **kwargs))
            retained.append(held)
            return held
        monkeypatch.setattr(lifecycle, '_open_lock', opened)
        monkeypatch.setattr(lifecycle, '_lock', lambda *_a: (_ for _ in ()).throw(primary))
    else:
        def failed_identity(value):
            if isinstance(value, int):
                retained.append(value)
                raise primary
            return identity(value)
        monkeypatch.setattr(lifecycle, '_identity', failed_identity)
        def failed_close(fd):
            if fd in retained:
                raise secondary
            return raw_close(fd)
        monkeypatch.setattr(os, 'close', failed_close)
    try:
        with pytest.raises(BaseException) as raised:
            owner.recover_prepared_release(case['session'], case['token'])
        assert raised.value is primary
        assert case['token'] in owner._recovery_owners
        recovery = owner._recovery_owners[case['token']]
        assert recovery.generation is None and recovery.has_retained_ownership()
        assert secondary in primary.recovery_errors
        with pytest.raises(JournalError):
            owner.close()
        with pytest.raises(JournalError, match='prior recovery'):
            owner.recover_prepared_release(case['session'], case['token'])
        if attachment == 'handle':
            monkeypatch.setattr(retained[0], 'close', retained[0].raw.close)
        else:
            monkeypatch.setattr(os, 'close', raw_close)
        assert recovery.close() and not recovery.has_retained_ownership()
        confirmed = True
    finally:
        # Baseline lacks registry tracking; independent handles still get closed.
        if attachment == 'handle':
            for held in retained:
                held.raw.close()
        elif not confirmed:
            for fd in retained:
                raw_close(fd)


def test_body_failure_keeps_secondary_native_and_sqlite_errors(recovery_case, monkeypatch):
    owner, case = recovery_case
    primary, native = RuntimeError('proof body'), OSError('native cleanup')
    lease = OSError('lease unlock secondary')
    rollback, close = OSError('rollback secondary'), OSError('close secondary')
    wrapped = inject_transaction(owner.journal, monkeypatch, 'record_release_recovery_cleanup',
                                 rollback=rollback, close=close)
    original = NativeHandle.close
    def failed(held):
        if str(held.path) == case['bridge'].intent.output_path:
            raise native
        return original(held)
    monkeypatch.setattr(NativeHandle, 'close', failed)
    from tikrec import lifecycle_lock
    monkeypatch.setattr(lifecycle_lock, '_unlock', lambda *_a: (_ for _ in ()).throw(lease))
    def fault(point):
        if point == 'after_recovery_proof':
            raise primary
    with pytest.raises(RuntimeError) as raised:
        owner.recover_prepared_release(case['session'], case['token'], fault=fault)
    assert raised.value is primary
    assert all(error in primary.recovery_secondary_errors for error in (native, lease, rollback, close))
    wrapped[0].rollback_error = wrapped[0].close_error = None
