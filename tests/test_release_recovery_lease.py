"""Lease errors and descriptor reuse never lose or adopt uncertain ownership."""

import os

import pytest

from tests.journal_assembly_helpers import managed_process
from tests.test_release_recovery_cleanup import recovery_case
from tikrec.session_journal_types import JournalError


@pytest.mark.parametrize('after', [False, True])
@pytest.mark.parametrize('unlock', [False, True])
def test_successful_proof_then_lease_cleanup_keeps_exact_errors(recovery_case, monkeypatch, after, unlock):
    from tikrec import lifecycle_lock
    owner, case = recovery_case
    first, second = OSError('lease unlock'), OSError('lease file close')
    files = []
    class FailedFile:
        def __init__(self, raw):
            self.raw, self.failed = raw, True
        def __getattr__(self, name):
            return getattr(self.raw, name)
        def close(self):
            if after or not self.failed:
                self.raw.close()
            if self.failed:
                raise second
    def fault(point):
        if point == 'after_recovery_authority':
            lease = owner._release_recovery.lease
            lease.handle = FailedFile(lease.handle)
            files.append(lease.handle)
    if unlock:
        monkeypatch.setattr(lifecycle_lock, '_unlock', lambda *_a: (_ for _ in ()).throw(first))
    with pytest.raises(OSError) as raised:
        owner.recover_prepared_release(case['session'], case['token'], fault=fault)
    assert raised.value is (first if unlock else second)
    assert second in raised.value.recovery_errors
    recovery = raised.value.recovery_owner
    assert recovery.has_retained_ownership() is (not after)
    evidence = owner.journal.release_recovery(case['token'])['cleanup']['evidence']
    assert evidence['cleanup_complete'] is False and len(owner.journal.status()['units']) == 1
    if not after:
        with pytest.raises(JournalError):
            owner.close()
    files[0].failed = False
    assert recovery.close()


@pytest.mark.parametrize('same_file', [False, True])
def test_reused_descriptor_cannot_close_an_unrelated_file(recovery_case, monkeypatch, tmp_path, same_file):
    from tikrec import lifecycle_lock
    owner, case = recovery_case
    first, second = OSError('lease setup'), OSError('lease close')
    identity, raw_close = lifecycle_lock._identity, os.close
    descriptors = []
    def failed_identity(value):
        if isinstance(value, int):
            descriptors.append(value)
            raise first
        return identity(value)
    def failed_close(fd):
        if fd in descriptors:
            raise second
        return raw_close(fd)
    with monkeypatch.context() as patch:
        patch.setattr(lifecycle_lock, '_identity', failed_identity)
        patch.setattr(os, 'close', failed_close)
        with pytest.raises(OSError) as raised:
            owner.recover_prepared_release(case['session'], case['token'])
        assert raised.value is first
    recovery, descriptor = first.recovery_owner, descriptors[0]
    raw_close(descriptor)
    unrelated = owner.root / lifecycle_lock.LOCK_NAME if same_file else tmp_path / 'unrelated-owned-file.bin'
    foreign = os.open(unrelated, os.O_RDWR if same_file else os.O_RDWR | os.O_CREAT | os.O_EXCL, 0o600)
    if foreign != descriptor:
        os.dup2(foreign, descriptor)
        raw_close(foreign)
    try:
        if same_file:
            assert lifecycle_lock._descriptor_identity(descriptor)[:3] == recovery.descriptor_identities[descriptor][:3]
        assert not recovery.close()
        assert os.fstat(descriptor).st_ino == unrelated.stat().st_ino
        assert recovery.has_retained_ownership()
        with pytest.raises(JournalError):
            owner.close()
        with pytest.raises(JournalError, match='prior recovery'):
            owner.recover_prepared_release(case['session'], case['token'])
    finally:
        raw_close(descriptor)
        # Independent fixture knowledge retires the externally closed original;
        # product cleanup deliberately refused to adopt the replacement descriptor.
        recovery.extra_descriptors.remove(descriptor)
        recovery.descriptor_identities.pop(descriptor)
