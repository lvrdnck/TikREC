"""Fresh authority, collisions, exact acknowledgement reconciliation and retained faults."""

import os
import sqlite3
from pathlib import Path

import pytest

from tests.journal_manifest_helpers import completing
from tests.journal_assembly_helpers import managed_process
from tikrec.journal_manifest import ManifestCompletionError

pytestmark = pytest.mark.skipif(os.name != "nt", reason="native completion faults")

BOUNDARIES = ['before_manifest_preparation', 'after_manifest_preparation', 'after_manifest_create',
    'before_manifest_write', 'after_manifest_write', 'after_manifest_staged_result',
    'before_manifest_preserve', 'after_manifest_preserve', 'after_manifest_preserved_result',
    'before_manifest_install', 'after_manifest_install', 'after_manifest_flush',
    'before_manifest_installed_result', 'after_manifest_installed_result']


@pytest.mark.parametrize('boundary', BOUNDARIES)
@pytest.mark.parametrize('mutation', ['inventory', 'output'])
def test_complete_inventory_and_output_are_rechecked_at_all_boundaries(completing, boundary, mutation):
    adapter, bridge, _, _, _ = completing
    runner = adapter.coordinator
    def fault(point):
        if point != boundary:
            return
        if mutation == 'inventory':
            (Path(bridge.intent.parts_path) / 'foreign-control.json').write_bytes(b'foreign evidence')
        else:
            held = runner.scratch.artifacts['candidate.mp4']
            os.lseek(held.fd, 0, 0)
            os.write(held.fd, b'changed output')
            held.flush()
    runner._fault = fault
    with pytest.raises(ManifestCompletionError):
        adapter.run()
    assert runner.guard.retained and runner.scratch.artifacts['candidate.mp4'].handle
    assert not adapter.close()


@pytest.mark.parametrize('target', ['stage', 'history', 'manifest'])
def test_last_native_boundary_collision_is_not_overwritten(completing, monkeypatch, target):
    adapter, _, _, _, _ = completing
    from tikrec import manifest_completion as module
    native = module.create_stage if target == 'stage' else module.rename_no_replace
    def collide(*args):
        cap = adapter.coordinator.manifest_owner
        path = cap.parent.path / (cap.stage_name if target == 'stage' else cap.history.name if target == 'history' else 'session.json')
        selected = target == 'stage' or args[2] == path.name
        if selected:
            path.write_bytes(b'late foreign control must survive')
        return native(*args)
    monkeypatch.setattr(module, 'create_stage' if target == 'stage' else 'rename_no_replace', collide)
    with pytest.raises(ManifestCompletionError):
        adapter.run()
    cap = adapter.capability
    path = cap.parent.path / (cap.stage_name if target == 'stage' else cap.history.name if target == 'history' else 'session.json')
    assert path.read_bytes() == b'late foreign control must survive'
    assert not any(s['phase'] == 'installed' for s in adapter.coordinator.journal.manifest_completion(
        adapter.coordinator.token)['steps'])


@pytest.mark.parametrize('phase', ['prepare', 'staged', 'preserved', 'installed'])
@pytest.mark.parametrize('unavailable', [False, True])
def test_ack_loss_has_one_exact_lookup_and_no_native_replay(completing, monkeypatch, phase, unavailable):
    adapter, _, _, _, _ = completing
    runner, calls, native_calls = adapter.coordinator, [], []
    from tikrec import manifest_completion as module
    native, lookup = module.rename_no_replace, runner.journal.operation
    selected = False
    def hook(kind, point):
        nonlocal selected
        if selected or point != 'after_commit':
            return
        hit = kind == 'prepare_manifest' if phase == 'prepare' else kind == 'manifest_step' and (
            ('staged' if not runner.manifest_owner.preserved else 'installed' if runner.manifest_owner.installed else 'preserved') == phase)
        if hit:
            selected = True
            raise OSError('lost exact acknowledgement')
    def operation(value):
        calls.append(value)
        if unavailable:
            raise OSError('lookup unavailable')
        return lookup(value)
    def rename(*args):
        native_calls.append(args[2])
        return native(*args)
    monkeypatch.setattr(runner.journal, 'operation', operation)
    monkeypatch.setattr(module, 'rename_no_replace', rename)
    runner.journal._fault = hook
    if unavailable:
        with pytest.raises(ManifestCompletionError):
            adapter.run()
    else:
        assert adapter.run()['state'] == 'installed'
    assert len(calls) == 1 and len(native_calls) <= 2
    with pytest.raises(Exception):
        adapter.run()
    assert len(native_calls) <= 2


@pytest.mark.parametrize('which', ['preserve', 'install'])
@pytest.mark.parametrize('after', [False, True])
def test_uncertain_native_return_retains_exact_owner_and_never_replays(completing, monkeypatch, which, after):
    adapter, _, _, _, raw = completing
    from tikrec import manifest_completion as module
    native, calls = module.rename_no_replace, []
    def rename(*args):
        selected = (args[2] == 'session.json') == (which == 'install')
        if selected:
            calls.append(args[0].handle)
            if after:
                native(*args)
            raise OSError('uncertain native return')
        return native(*args)
    monkeypatch.setattr(module, 'rename_no_replace', rename)
    with pytest.raises(ManifestCompletionError) as caught:
        adapter.run()
    assert str(caught.value.original) == 'uncertain native return' and len(calls) == 1
    assert adapter.capability.predecessor.read_control() == raw
    assert adapter.capability.stage.handle is not None and adapter.capability.predecessor.handle is not None
    with pytest.raises(Exception):
        adapter.capability.complete()
    assert len(calls) == 1 and not adapter.close()


@pytest.mark.parametrize('failure', ['write', 'stage_flush', 'install_flush', 'stage_proof', 'native_proof'])
def test_write_flush_and_partial_acquisition_failures_keep_first_owner(completing, monkeypatch, failure):
    adapter, _, _, _, _ = completing
    from tikrec import manifest_native, manifest_completion
    error = OSError('first native control failure')
    def fail(*_):
        raise error
    if failure == 'write':
        monkeypatch.setattr(manifest_completion, 'write_stage', fail)
    elif failure == 'stage_proof':
        native = manifest_completion.create_stage
        def create(*args):
            native(*args)
            raise error
        monkeypatch.setattr(manifest_completion, 'create_stage', create)
    elif failure == 'native_proof':
        from tikrec.attempt_scratch import ScratchHandle
        identity = ScratchHandle._path_identity
        def proof(held):
            if held.path.name.endswith('.successor.json'):
                raise error
            return identity(held)
        monkeypatch.setattr(ScratchHandle, '_path_identity', proof)
    else:
        def hook(point):
            if point == ('after_manifest_create' if failure == 'stage_flush' else 'before_manifest_flush'):
                monkeypatch.setattr(adapter.coordinator.manifest_owner.stage, 'flush', fail)
        adapter.coordinator._fault = hook
    runner = adapter.coordinator
    hold = runner.journal.scratch
    def secondary(token):
        if runner.cancelled.is_set():
            raise OSError('secondary persistence failure')
        return hold(token)
    monkeypatch.setattr(runner.journal, 'scratch', secondary)
    with pytest.raises(ManifestCompletionError) as caught:
        adapter.run()
    assert caught.value.original is error and adapter.capability.stage.handle is not None
    assert any('secondary' in str(e) for e in runner.errors)


def test_predecessor_byte_conflict_and_immutable_evidence(completing, monkeypatch):
    adapter, _, _, _, _ = completing
    def hook(point):
        if point == 'before_manifest_preparation':
            held = adapter.coordinator.manifest_owner.predecessor
            monkeypatch.setattr(held, 'read_control', lambda: b'{}')
    adapter.coordinator._fault = hook
    with pytest.raises(ManifestCompletionError):
        adapter.run()
    assert adapter.coordinator.journal.manifest_completion(adapter.coordinator.token) is None


def test_successor_bytes_and_receipts_cannot_be_mutated(completing):
    adapter, _, _, _, _ = completing
    adapter.run()
    runner = adapter.coordinator
    for table in ['manifest_preparations', 'manifest_steps']:
        for command in [f'UPDATE {table} SET token=token', f'DELETE FROM {table}']:
            with sqlite3.connect(runner.journal.path) as db, pytest.raises(sqlite3.IntegrityError):
                db.execute(command)


@pytest.mark.parametrize('field', ['predecessor', 'successor', 'namespace', 'publication'])
def test_forged_control_binding_is_refused_before_any_write(completing, field):
    adapter, _, _, _, _ = completing
    def hook(point):
        if point == 'before_manifest_preparation':
            binding = adapter.coordinator.manifest_owner.binding
            if field in {'predecessor', 'successor'}:
                binding[field]['sha256'] = '0' * 64
            elif field == 'namespace':
                binding[field]['history'] = 'foreign.json'
            else:
                binding[field]['result_operation'] = adapter.coordinator.uuid()
    adapter.coordinator._fault = hook
    with pytest.raises(ManifestCompletionError):
        adapter.run()
    assert adapter.capability.stage is None
    assert adapter.coordinator.journal.manifest_completion(adapter.coordinator.token) is None


@pytest.mark.parametrize('boundary', ['after_manifest_staged_result', 'before_manifest_install', 'after_manifest_install'])
def test_successor_bytes_with_restored_native_stamp_cannot_inherit_proof(completing, boundary):
    import ctypes
    from ctypes import wintypes
    adapter, _, _, _, _ = completing
    def hook(point):
        if point != boundary:
            return
        held = adapter.coordinator.manifest_owner.stage
        stamp = held.stamp
        os.lseek(held.fd, 0, 0)
        os.write(held.fd, b'changed!')
        held.flush()
        written = int(stamp.split(':')[-1], 16)
        restored = wintypes.FILETIME(written & 0xffffffff, written >> 32)
        held.api.SetFileTime.argtypes = (wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
                                       ctypes.POINTER(wintypes.FILETIME))
        held.api.SetFileTime.restype = wintypes.BOOL
        assert held.api.SetFileTime(held.handle, None, None, ctypes.byref(restored))
        assert held.stamp == stamp
    adapter.coordinator._fault = hook
    with pytest.raises(ManifestCompletionError):
        adapter.run()
    assert not any(s['phase'] == 'installed' for s in adapter.coordinator.journal.manifest_completion(
        adapter.coordinator.token)['steps'])


@pytest.mark.parametrize('conflict', ['parent', 'volume', 'predecessor'])
def test_native_parent_volume_and_predecessor_identity_conflicts_refuse_preparation(completing, conflict):
    from tikrec.session_journal_types import ArtifactIdentity
    adapter, _, _, _, _ = completing
    def hook(point):
        if point != 'before_manifest_preparation':
            return
        cap = adapter.coordinator.manifest_owner
        held = cap.predecessor if conflict == 'predecessor' else cap.parent
        identity = held.identity
        held.identity = ArtifactIdentity('volume{00000000-0000-0000-0000-000000000000}'
            if conflict == 'volume' else identity.volume,
            identity.components if conflict == 'volume' else identity.components + ('foreign',))
    adapter.coordinator._fault = hook
    with pytest.raises(ManifestCompletionError):
        adapter.run()
    assert adapter.capability.stage is None
    assert adapter.coordinator.journal.manifest_completion(adapter.coordinator.token) is None
