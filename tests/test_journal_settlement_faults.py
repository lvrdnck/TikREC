"""Prepared cleanup never becomes release through drift, failure or cancellation."""

import copy
import os
from pathlib import Path

import pytest

from tests.journal_settlement_helpers import settling
from tests.journal_assembly_helpers import managed_process
from tikrec.journal_settlement import SettlementError
from tikrec.session_journal_types import JournalUncertain

pytestmark = pytest.mark.skipif(os.name != 'nt', reason='native Windows success release')


@pytest.mark.parametrize('boundary', ['before_release_preparation', 'after_release_preparation',
    'after_release_resource_input_0', 'after_release_cleanup', 'before_terminal_release', 'after_terminal_release'])
def test_boundary_failure_preserves_exact_committed_facts(settling, boundary):
    adapter, _, original, _, _ = settling
    runner = adapter.coordinator
    first = OSError('first boundary failure')
    def fault(point):
        if point == boundary:
            raise first
    runner._fault = fault
    with pytest.raises(SettlementError) as error:
        adapter.run()
    assert error.value.original is first
    record = runner.journal.settlement(runner.token)
    terminal = boundary == 'after_terminal_release'
    assert (record is not None) == (boundary != 'before_release_preparation')
    assert runner.journal.session(original['id'])['task']['state'] == ('completed' if terminal else 'running')
    assert len(runner.journal.status()['units']) == (0 if terminal else 1)
    if terminal:
        assert adapter.cleanup_evidence()['terminal_result']['state'] == 'released'


@pytest.mark.parametrize('when', ['before_release_preparation', 'after_release_preparation'])
@pytest.mark.parametrize('drift', ['parts', 'scratch', 'output', 'successor', 'history', 'resource'])
def test_held_proof_drift_cannot_return_capacity(settling, monkeypatch, when, drift):
    adapter, bridge, original, _, _ = settling
    runner = adapter.coordinator
    def fault(point):
        if point != when:
            return
        if drift == 'parts':
            (Path(bridge.intent.parts_path) / 'foreign.json').write_bytes(b'foreign')
        elif drift == 'scratch':
            (runner.scratch.path / 'foreign.bin').write_bytes(b'foreign')
        elif drift == 'history':
            monkeypatch.setattr(runner.manifest_owner.predecessor, 'identity', runner.manifest_owner.stage.identity)
        elif drift == 'resource':
            monkeypatch.setattr(runner.manifest_owner, 'stage', copy.copy(runner.manifest_owner.stage))
        else:
            held = runner.manifest_owner.stage if drift == 'successor' else runner.scratch.artifacts['candidate.mp4']
            # Change proof observation without changing retained fixture bytes.
            monkeypatch.setattr(type(held), 'size', property(lambda self: 1 if self is held else size.fget(self)))
    size = None
    if drift in {'successor', 'output'}:
        from tikrec.attempt_scratch import ScratchHandle
        size = ScratchHandle.size
    runner._fault = fault
    with pytest.raises(SettlementError):
        adapter.run()
    assert runner.journal.session(original['id'])['task']['state'] == 'running'
    assert len(runner.journal.status()['units']) == 1
    assert runner.scratch.artifacts['candidate.mp4'].handle is not None
    assert runner.manifest_owner.predecessor.handle is not None


@pytest.mark.parametrize('after', [False, True])
def test_cancellation_on_either_side_of_preparation(settling, after):
    adapter, _, original, _, _ = settling
    runner = adapter.coordinator
    def fault(point):
        if point == ('after_release_preparation' if after else 'before_release_preparation'):
            adapter.cancel()
    runner._fault = fault
    if after:
        assert adapter.run()['state'] == 'released'
        assert not runner.journal.status()['units']
    else:
        with pytest.raises(SettlementError):
            adapter.run()
        assert runner.journal.settlement(runner.token) is None
        assert runner.journal.session(original['id'])['task']['state'] == 'running'
        assert len(runner.journal.status()['units']) == 1


@pytest.mark.parametrize('kind', ['prepare_release', 'record_release_cleanup', 'settle_owned_success'])
@pytest.mark.parametrize('lookup_available', [False, True])
def test_lost_acknowledgement_only_reconciles_one_exact_operation(settling, monkeypatch, kind, lookup_available):
    adapter, _, original, _, _ = settling
    runner, calls = adapter.coordinator, []
    lookup = runner.journal.operation
    first = OSError('lost acknowledgement')
    def transaction(selected, point):
        if selected == kind and point == 'after_commit':
            raise first
    def operation(identity):
        calls.append(identity)
        if not lookup_available:
            raise OSError('lookup unavailable')
        return lookup(identity)
    runner.journal._fault = transaction
    monkeypatch.setattr(runner.journal, 'operation', operation)
    if lookup_available:
        assert adapter.run()['state'] == 'released'
    else:
        with pytest.raises(SettlementError) as error:
            adapter.run()
        assert isinstance(error.value.original, JournalUncertain)
    assert len(calls) == 1
    terminal = lookup_available or kind == 'settle_owned_success'
    assert runner.journal.session(original['id'])['phase'] == ('completed' if terminal else 'running')
    assert len(runner.journal.status()['units']) == (0 if terminal else 1)
    assert runner.journal._read(lambda db: db.execute('SELECT count(*) FROM operations WHERE kind=?',
        (kind,)).fetchone()[0]) == 1


@pytest.mark.parametrize('kind', ['prepare_release', 'record_release_cleanup', 'settle_owned_success'])
@pytest.mark.parametrize('boundary', ['after_begin', 'after_writes', 'before_commit'])
def test_failed_release_transaction_never_partially_returns_capacity(settling, kind, boundary):
    adapter, _, original, _, _ = settling
    runner = adapter.coordinator
    first = RuntimeError('transaction failure')
    def fault(selected, point):
        if selected == kind and point == boundary:
            raise first
    runner.journal._fault = fault
    with pytest.raises(SettlementError) as error:
        adapter.run()
    assert error.value.original is first
    current = runner.journal.session(original['id'])
    assert current['task']['state'] == 'running'
    assert current['rooms'] == original['rooms'] and current['artifacts'] == original['artifacts']
    assert len(runner.journal.status()['units']) == 1
    assert runner.journal._read(lambda db: db.execute('SELECT count(*) FROM release_results').fetchone()[0]) == 0


@pytest.mark.parametrize('window', ['after_begin', 'before_commit', 'after_commit'])
def test_real_output_change_with_restored_native_stamp_never_inherits_release_proof(settling, window):
    import ctypes
    from ctypes import wintypes
    adapter, _, _, _, _ = settling
    runner, changed = adapter.coordinator, []
    def fault(kind, point):
        if kind != 'prepare_release' or point != window:
            return
        held = runner.scratch.artifacts['candidate.mp4']
        stamp = held.stamp
        os.lseek(held.fd, 0, 0)
        os.write(held.fd, b'changed!')
        held.flush()
        written = int(stamp.split(':')[-1], 16)
        restored = wintypes.FILETIME(written & 0xffffffff, written >> 32)
        held.api.SetFileTime.argtypes = (wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(wintypes.FILETIME))
        held.api.SetFileTime.restype = wintypes.BOOL
        assert held.api.SetFileTime(held.handle, None, None, ctypes.byref(restored))
        assert held.stamp == stamp
        changed.append(held)
    runner.journal._fault = fault
    with pytest.raises(SettlementError) as error:
        adapter.run()
    assert 'prepared output bytes changed' in str(error.value.original)
    assert len(changed) == 1 and changed[0].handle is not None
    candidate = runner.journal.scratch(runner.token)['candidate']
    # Native protection forbids reopening; prove drift through that exact owner.
    assert runner.scratch._hash(changed[0]) != candidate['sha256']
    assert runner.journal.settlement(runner.token)['state'] == 'cleanup_pending'
    assert len(runner.journal.status()['units']) == 1
    assert runner.journal._read(lambda db: db.execute('SELECT count(*) FROM release_results').fetchone()[0]) == 0
