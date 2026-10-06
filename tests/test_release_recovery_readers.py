"""Actual recovery-only SQLite reader failures cannot silently lose ownership."""

import sqlite3

import pytest

from tests.manifest_fence_helpers import ConnectionFaults
from tests.test_release_recovery_cleanup import recovery_case
from tests.journal_assembly_helpers import managed_process
from tikrec.capture_handoff_native import NativeHandle
from tikrec.session_journal_types import JournalError


def test_partial_sqlite_factory_cannot_replace_its_body_error_or_drop_its_connection(
        recovery_case, monkeypatch):
    owner, case = recovery_case
    first, secondary = OSError('SQLite policy setup'), OSError('SQLite factory close')
    connect, wrapped = sqlite3.connect, []
    class Failed(ConnectionFaults):
        def execute(self, sql, *args):
            if sql == 'PRAGMA synchronous=EXTRA':
                raise first
            return super().execute(sql, *args)
    def once(*args, **kwargs):
        monkeypatch.setattr(sqlite3, 'connect', connect)
        connection = Failed(connect(*args, **kwargs), close=secondary)
        wrapped.append(connection)
        return connection
    monkeypatch.setattr(sqlite3, 'connect', once)
    with pytest.raises(OSError) as raised:
        owner.recover_prepared_release(case['session'], case['token'])
    assert raised.value is first and secondary in first.recovery_secondary_errors
    recovery = first.recovery_owner
    assert recovery.has_retained_ownership() and recovery.readers[0].connection is wrapped[0]
    with pytest.raises(JournalError):
        owner.close()
    wrapped[0].close_error = None
    assert recovery.close()


@pytest.mark.parametrize('phase', ['initial', 'proof', 'lookup'])
def test_observational_reader_cleanup_is_exact_and_registered(recovery_case, monkeypatch, phase):
    owner, case = recovery_case
    first, secondary = sqlite3.OperationalError('reader rollback'), sqlite3.OperationalError('reader close')
    ack = OSError('terminal acknowledgement')
    connect, retained = owner.journal._connect, []
    def once():
        monkeypatch.setattr(owner.journal, '_connect', connect)
        wrapped = ConnectionFaults(connect(), rollback=first, close=secondary)
        retained.append(wrapped)
        return wrapped
    def journal_fault(kind, point):
        if phase == 'lookup' and kind == 'settle_release_recovery' and point == 'after_commit':
            monkeypatch.setattr(owner.journal, '_connect', once)
            raise ack
    def fault(point):
        if phase == 'proof' and point == 'after_recovery_authority':
            monkeypatch.setattr(owner.journal, '_connect', once)
    owner.journal._fault = journal_fault
    if phase == 'initial':
        monkeypatch.setattr(owner.journal, '_connect', once)
    with pytest.raises(BaseException) as raised:
        owner.recover_prepared_release(case['session'], case['token'], fault=fault)
    assert raised.value is (ack if phase == 'lookup' else first)
    recovery = raised.value.recovery_owner
    assert first in raised.value.recovery_errors and secondary in raised.value.recovery_errors
    assert recovery.has_retained_ownership()
    assert any(held is recovery for held in owner._recovery_owners.values())
    if phase == 'lookup':
        assert recovery.terminal_result['state'] == 'released'
        assert owner.journal.status()['units'] == []
    else:
        assert len(owner.journal.status()['units']) == 1
    with pytest.raises(JournalError):
        owner.close()
    retained[0].rollback_error = retained[0].close_error = None
    assert recovery.close()
    owner.journal._fault = None
    assert owner.recover_prepared_release(case['session'], case['token'])['state'] == 'released'


def test_partial_native_factory_keeps_the_original_and_its_exact_handle(recovery_case, monkeypatch):
    owner, case = recovery_case
    first, secondary = OSError('native proof acquisition'), OSError('native factory cleanup')
    information, close = NativeHandle._information, NativeHandle.close
    fired = []
    def failed_information(held):
        if str(held.path) == case['bridge'].intent.output_path and not fired:
            fired.append(True)
            raise first
        return information(held)
    def failed_close(held):
        if str(held.path) == case['bridge'].intent.output_path and held.handle is not None:
            raise secondary
        return close(held)
    with monkeypatch.context() as patch:
        patch.setattr(NativeHandle, '_information', failed_information)
        patch.setattr(NativeHandle, 'close', failed_close)
        with pytest.raises(OSError) as raised:
            owner.recover_prepared_release(case['session'], case['token'])
        assert raised.value is first and secondary in first.recovery_secondary_errors
        recovery = first.recovery_owner
        assert recovery.objects['scratch:candidate.mp4'].handle is not None
        assert recovery.has_retained_ownership()
        assert recovery.lease.handle.closed
        with pytest.raises(JournalError):
            owner.close()
    assert recovery.close()
    assert owner.recover_prepared_release(case['session'], case['token'])['state'] == 'released'


def test_cleanup_diagnostics_are_bounded_without_losing_owners(recovery_case, monkeypatch):
    owner, case = recovery_case
    failures = []
    def failed(_held):
        error = OSError('native close ' + str(len(failures)))
        failures.append(error)
        raise error
    def fault(point):
        if point.startswith('after_recovery_cleanup_resource_'):
            error = RuntimeError('cleanup hook ' + str(len(failures)))
            failures.append(error)
            raise error
    monkeypatch.setattr(NativeHandle, 'close', failed)
    with pytest.raises(OSError) as raised:
        owner.recover_prepared_release(case['session'], case['token'], fault=fault)
    assert raised.value is failures[0] and len(failures) > 32
    assert len(raised.value.recovery_errors) == 32
    assert raised.value.recovery_errors_dropped == len(failures) - 32
    evidence = owner.journal.release_recovery(case['token'])['cleanup']['evidence']
    assert len(evidence['diagnostics']) == 32
    assert evidence['diagnostics_dropped'] == len(failures) - 32
    assert raised.value.recovery_owner.has_retained_ownership()
    assert len(owner.journal.status()['units']) == 1
