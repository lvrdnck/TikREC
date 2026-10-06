"""Prepared-success restart recovery remains explicit, bounded, and exact-once."""

import hashlib
import json
import os
import sqlite3
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier, get_ident

import pytest

from tests.capture_handoff_helpers import authority
from tests.journal_recovery_helpers import hashes, prepared_success
from tests.journal_settlement_helpers import adapter_for, independent_cleanup
from tests.journal_assembly_helpers import managed_process, queue_media
from tikrec.capture_handoff_authority import CaptureAuthority, operation_id
from tikrec.capture_handoff_native import NativeHandle
from tikrec.journal_settlement import SettlementError
from tikrec.lifecycle_lock import LifecycleBusy
from tikrec.session_journal_types import JournalError


@pytest.mark.parametrize(('different', 'interrupted'), [(False, False), (True, False), (False, True)])
def test_recovery_preserves_media_and_then_explicitly_processes_fifo(
        tmp_path, managed_process, monkeypatch, different, interrupted):
    owner = authority(tmp_path)
    adapters = []
    try:
        case = prepared_success(owner, tmp_path, managed_process, different=different,
                                later=not interrupted, interrupted=interrupted)
        adapters.append(case['adapter'])
        original_bytes = hashes(owner.root)
        source_bytes = {str(path): hashlib.sha256(path.read_bytes()).hexdigest()
                        for path in tmp_path.glob('*.flv')}
        output = Path(case['bridge'].intent.output_path)
        output_hash = hashlib.sha256(output.read_bytes()).hexdigest()
        history = Path(case['bridge'].intent.parts_path) / f'.tikrec-manifest-{case["token"]}.original.json'
        installed = Path(case['bridge'].intent.parts_path) / 'session.json'
        installed_values = json.loads(installed.read_bytes())
        assert installed_values['interrupted'] is interrupted
        completion = owner.journal.manifest_completion(case['token'])
        from tikrec.manifest_successor_values import unpacked
        predecessor, successor = completion['binding']['predecessor'], completion['binding']['successor']
        assert history.read_bytes() == unpacked(predecessor)
        assert installed.read_bytes() == unpacked(successor)
        assert case['adapter'].manifest.publication.validation.assembly.plan.stream_copy is (not different)
        with monkeypatch.context() as patch:
            patch.setattr(subprocess, 'run', lambda *_a, **_k: pytest.fail('recovery launched a process'))
            result = owner.recover_prepared_release(case['session'], case['token'])
        assert result['state'] == 'released' and result['recovery_result']['evidence']['returned_units'] == 1
        assert owner.journal.release_recovery(case['token'])['head']['generation'] == 1
        assert hashes(owner.root) == original_bytes
        assert {str(path): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in tmp_path.glob('*.flv')} == source_bytes
        assert hashlib.sha256(output.read_bytes()).hexdigest() == output_hash
        assert json.loads(installed.read_bytes()) == installed_values
        current = owner.journal.session(case['session'])
        assert current['phase'] == current['task']['state'] == 'completed'
        assert current['artifacts'] == current['rooms'] == []
        assert len(owner.journal.status()['units']) == (1 if case['later'] else 0)
        before_repeat = owner.journal.path.read_bytes()
        with monkeypatch.context() as patch:
            patch.setattr(NativeHandle, '__init__', lambda *_a, **_k: pytest.fail('terminal retry reopened media'))
            assert owner.recover_prepared_release(case['session'], case['token']) == result
        assert owner.journal.path.read_bytes() == before_repeat
        if case['later']:
            next_adapter = adapter_for(owner, managed_process)
            adapters.append(next_adapter)
            next_result = next_adapter.run()
            assert next_result['session_id'] == case['later']['id']
            assert next_result['state'] == 'released' and next_result['returned_units'] == 1
        assert owner.journal.status()['units'] == []
    finally:
        for adapter in adapters:
            independent_cleanup(adapter)
        owner.close()


@pytest.mark.parametrize('target', ['output', 'control', 'inventory', 'alias'])
def test_proof_drift_keeps_task_capacity_and_does_not_repair_files(tmp_path, managed_process, target):
    owner = authority(tmp_path)
    case = None
    try:
        case = prepared_success(owner, tmp_path, managed_process)
        if target in {'output', 'alias'}:
            path = Path(case['bridge'].intent.output_path)
        elif target == 'control':
            seal = owner.journal.session(case['session'])['seal']
            index = next(i for i, item in enumerate(seal['artifacts']) if item['control_hash'] is not None)
            key = f'input:{index + 3}'
            path = Path(next(item['evidence']['path'] for item in case['record']['preparation']['binding']['resources']
                             if item['key'] == key))
        else:
            path = Path(case['bridge'].intent.parts_path) / 'unexpected-recovery-evidence.bin'
        if target == 'inventory':
            path.write_bytes(b'fixture drift')
        elif target == 'alias':
            alias = path.with_name('recovery-hardlink-alias.mp4')
            os.link(path, alias)
        else:
            stat = path.stat()
            with path.open('r+b') as handle:
                handle.seek(0)
                byte = handle.read(1)
                handle.seek(0)
                handle.write(bytes([byte[0] ^ 1]))
            os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns))
        changed = hashes(owner.root)
        pattern = 'multiply-linked' if target == 'alias' else 'drifted|changed'
        with pytest.raises(JournalError, match=pattern):
            owner.recover_prepared_release(case['session'], case['token'])
        assert hashes(owner.root) == changed
        assert owner.journal.settlement(case['token'])['state'] == 'cleanup_confirmed'
        recovery = owner.journal.release_recovery(case['token'])
        assert recovery['head']['state'] == 'uncertain'
        assert recovery['proof'] is None and recovery['cleanup'] is not None
        assert len(owner.journal.status()['units']) == 1
        if target == 'alias':
            alias.unlink()
    finally:
        if case:
            independent_cleanup(case['adapter'])
        owner.close()


@pytest.mark.parametrize('fault', ['close_ack', 'close_error', 'cancel'])
def test_incomplete_recovery_cleanup_stays_pinned_and_new_generation_can_finish(
        tmp_path, managed_process, monkeypatch, fault):
    owner = authority(tmp_path)
    case = None
    try:
        case = prepared_success(owner, tmp_path, managed_process)
        if fault in {'close_ack', 'close_error'}:
            original_close = NativeHandle.close
            fired = False
            output = Path(case['bridge'].intent.output_path)
            def close_with_lost_ack(held):
                nonlocal fired
                if held.path == output and not fired:
                    fired = True
                    if fault == 'close_error':
                        raise OSError('injected unconfirmed native close')
                    original_close(held)
                    raise OSError('injected close acknowledgement loss')
                original_close(held)
            monkeypatch.setattr(NativeHandle, 'close', close_with_lost_ack)
            expected = JournalError
        else:
            def cancellation(point):
                if point == 'after_recovery_resource_input_0':
                    raise RuntimeError('explicit recovery cancellation')
            expected = RuntimeError
        with pytest.raises(expected):
            owner.recover_prepared_release(case['session'], case['token'],
                fault=cancellation if fault == 'cancel' else (lambda _: None))
        interrupted = owner.journal.release_recovery(case['token'])
        assert interrupted['head']['generation'] == 1 and interrupted['head']['state'] == 'uncertain'
        assert len(owner.journal.status()['units']) == 1
        monkeypatch.undo()
        if fault == 'close_error':
            retained = owner._recovery_owners[case['token']]
            retained.objects['scratch:candidate.mp4'].close()
            assert not retained.has_retained_ownership()
        completed = owner.recover_prepared_release(case['session'], case['token'])
        assert completed['state'] == 'released'
        history = owner.journal.release_recovery(case['token'])
        assert history['head']['generation'] == 2
        assert owner.journal.status()['units'] == []
    finally:
        if case:
            independent_cleanup(case['adapter'])
        owner.close()


@pytest.mark.parametrize('lost_operation', ['record_release_recovery_proof', 'settle_release_recovery'])
def test_acknowledgement_loss_and_stale_original_callbacks_are_fenced(
        tmp_path, managed_process, lost_operation):
    owner = authority(tmp_path)
    case = None
    try:
        case = prepared_success(owner, tmp_path, managed_process)
        adapter, runner = case['adapter'], case['adapter'].coordinator
        capability = adapter.capability
        record = owner.journal.settlement(case['token'])
        def stale(kind, value):
            arguments = [runner.token, runner.owner, runner.revision, value]
            capability.call_thread = get_ident()
            capability.call_authority = (kind, *arguments)
            try:
                with pytest.raises(JournalError, match='fenced'):
                    getattr(owner.journal, kind)(operation_id(), *arguments, capability=capability)
            finally:
                capability.call_thread = capability.call_authority = None
        acknowledgements = {'lost': False}
        def journal_fault(kind, boundary):
            if kind == lost_operation and boundary == 'after_commit' and not acknowledgements['lost']:
                acknowledgements['lost'] = True
                raise OSError('injected proof receipt acknowledgement loss')
        owner.journal._fault = journal_fault
        def recovery_fault(point):
            if point == 'after_recovery_authority':
                stale('record_release_cleanup', record['cleanup']['evidence'])
                stale('settle_owned_success', {'preparation_operation': record['preparation']['operation'],
                    'cleanup_operation': record['cleanup']['operation'],
                    'binding_hash': capability.binding_hash, 'cleanup_complete': True, 'returned_units': 1})
        result = owner.recover_prepared_release(case['session'], case['token'], fault=recovery_fault)
        owner.journal._fault = None
        assert acknowledgements['lost'] and result['state'] == 'released'
        assert owner.journal.release_recovery(case['token'])['head']['generation'] == 1
        with sqlite3.connect(owner.journal.path) as connection:
            assert connection.execute('SELECT count(*) FROM release_results WHERE token=?',
                                      (case['token'],)).fetchone()[0] == 0
            assert connection.execute('SELECT count(*) FROM release_recovery_results WHERE token=?',
                                      (case['token'],)).fetchone()[0] == 1
    finally:
        owner.journal._fault = None
        if case:
            independent_cleanup(case['adapter'])
        owner.close()


def test_competing_recoverers_serialize_and_foreign_authority_is_refused(tmp_path, managed_process):
    owner = authority(tmp_path)
    case = None
    try:
        case = prepared_success(owner, tmp_path, managed_process)
        with pytest.raises(LifecycleBusy):
            CaptureAuthority(owner.journal, owner.root)
        barrier = Barrier(3)
        def recover():
            barrier.wait()
            return owner.recover_prepared_release(case['session'], case['token'])
        with ThreadPoolExecutor(max_workers=2) as pool:
            calls = [pool.submit(recover) for _ in range(2)]
            barrier.wait()
            results = [call.result(timeout=60) for call in calls]
        assert all(result['state'] == 'released' for result in results)
        assert owner.journal.release_recovery(case['token'])['head']['generation'] == 1
        assert len(owner.journal.status()['units']) == 0
    finally:
        if case:
            independent_cleanup(case['adapter'])
        owner.close()


def test_live_original_owner_and_earlier_phase_are_not_recoverable(tmp_path, managed_process):
    owner = authority(tmp_path)
    try:
        bridge, _ = queue_media(owner, tmp_path)
        live = adapter_for(owner, managed_process)
        live.coordinator._fault = lambda point: (_raise(point)
            if point == 'after_release_preparation' else None)
        with pytest.raises(SettlementError):
            live.run()
        with pytest.raises(JournalError, match='live attempt owner'):
            owner.recover_prepared_release(bridge.intent.session_id, live.coordinator.token)
        assert owner.journal.release_recovery(live.coordinator.token) is None
        assert owner.journal.settlement(live.coordinator.token)['state'] == 'cleanup_pending'
        independent_cleanup(live)
        assert len(owner.journal.status()['units']) == 1
    finally:
        owner.close()


def test_unprepared_attempt_remains_unsupported_and_observational(tmp_path, managed_process):
    owner = authority(tmp_path)
    try:
        bridge, _ = queue_media(owner, tmp_path)
        adapter = adapter_for(owner, managed_process)
        adapter.coordinator._fault = lambda point: (_raise(point) if point == 'after_claim' else None)
        with pytest.raises(SettlementError):
            adapter.run()
        before = owner.journal.path.read_bytes()
        with pytest.raises(JournalError, match='before successful release preparation'):
            owner.recover_prepared_release(bridge.intent.session_id, adapter.coordinator.token)
        assert owner.journal.path.read_bytes() == before
        assert owner.journal.release_recovery(adapter.coordinator.token) is None
        assert len(owner.journal.status()['units']) == 1
        independent_cleanup(adapter)
    finally:
        owner.close()


def _raise(point):
    raise RuntimeError(point)
