"""Actual Windows close failures keep exact ownership despite Python.closed."""

import ctypes
import msvcrt
from ctypes import wintypes

import pytest

from tests.journal_assembly_helpers import managed_process
from tests.test_release_recovery_cleanup import recovery_case
from tikrec.session_journal_types import JournalError


def protection(handle, enabled):
    """Toggle Windows' real close protection on a disposable recovery handle."""
    api = ctypes.WinDLL('kernel32', use_last_error=True)
    api.SetHandleInformation.argtypes = (wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD)
    api.SetHandleInformation.restype = wintypes.BOOL
    assert api.SetHandleInformation(handle, 2, 2 if enabled else 0)


@pytest.mark.parametrize('resource', ['lease', 'native', 'partial_handle', 'partial_descriptor'])
def test_closed_python_stream_with_live_native_lease_stays_registered(recovery_case, monkeypatch, resource):
    from tikrec import lifecycle_lock
    owner, case = recovery_case
    protected = []
    first = OSError('partial acquisition before generation')
    def protect(handle):
        protection(handle, True)
        protected.append(handle)
    def fault(point):
        if resource == 'lease' and point == 'after_recovery_authority':
            lease = owner._release_recovery.lease
            protect(msvcrt.get_osfhandle(lease.handle.fileno()))
        elif resource == 'native' and point == 'after_recovery_proof':
            protect(owner._release_recovery.objects['scratch:candidate.mp4'].handle)
    if resource == 'partial_handle':
        def failed_lock(handle, *_args):
            protect(msvcrt.get_osfhandle(handle.fileno()))
            raise first
        monkeypatch.setattr(lifecycle_lock, '_lock', failed_lock)
    elif resource == 'partial_descriptor':
        identity = lifecycle_lock._identity
        def failed_identity(value):
            if isinstance(value, int):
                protect(msvcrt.get_osfhandle(value))
                raise first
            return identity(value)
        monkeypatch.setattr(lifecycle_lock, '_identity', failed_identity)
    completed = False
    try:
        with pytest.raises(OSError) as raised:
            owner.recover_prepared_release(case['session'], case['token'], fault=fault)
        recovery = raised.value.recovery_owner
        if resource.startswith('partial'):
            assert raised.value is first and recovery.generation is None
            assert raised.value.recovery_secondary_errors
        elif resource == 'lease':
            assert recovery.lease.handle.closed
        assert recovery.has_retained_ownership()
        assert owner._recovery_owners[case['token']] is recovery
        with pytest.raises(JournalError):
            owner.close()
        with pytest.raises(JournalError, match='prior recovery'):
            owner.recover_prepared_release(case['session'], case['token'])
        if not resource.startswith('partial'):
            evidence = owner.journal.release_recovery(case['token'])['cleanup']['evidence']
            assert evidence['cleanup_complete'] is False
            key = 'lease' if resource == 'lease' else 'scratch:candidate.mp4'
            assert next(item for item in evidence['resources'] if item['key'] == key)['closed'] is False
        assert len(owner.journal.status()['units']) == 1
        for handle in protected:
            protection(handle, False)
        monkeypatch.undo()
        assert recovery.close() and not recovery.has_retained_ownership()
        assert not any(g.retained for g in recovery.native_close_guards)
        completed = True
    finally:
        for handle in protected if not completed else ():
            protection(handle, False)
            # Independent cleanup also makes the deliberately failing baseline safe.
            api = ctypes.WinDLL('kernel32', use_last_error=True)
            api.CloseHandle.argtypes = (wintypes.HANDLE,)
            api.CloseHandle.restype = wintypes.BOOL
            api.CloseHandle(handle)
    assert owner.recover_prepared_release(case['session'], case['token'])['state'] == 'released'
