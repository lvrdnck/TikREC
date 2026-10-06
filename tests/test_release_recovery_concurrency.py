"""R13: real captures keep progressing while recovery owns its proof resources."""

from concurrent.futures import ThreadPoolExecutor, TimeoutError
from pathlib import Path
from threading import Event, get_ident
import os

import pytest

from tests.capture_handoff_helpers import authority, local_media, observations, reserve
from tests.journal_assembly_helpers import managed_process
from tests.journal_recovery_helpers import hashes, prepared_success
from tests.journal_settlement_helpers import adapter_for, independent_cleanup
from tikrec.release_recovery_native import RecoveryNativeProof
from tikrec.session_journal_types import JournalError
from tikrec.source import iter_tags
from tikrec.capture_handoff_authority import operation_id
from tests.test_journal_settlement_cleanup import inject_transaction


def test_two_connected_captures_handoff_during_recovery_hash(tmp_path, managed_process, monkeypatch):
    owner = authority(tmp_path)
    case = prepared_success(owner, tmp_path, managed_process)
    before = hashes(owner.root)
    data = local_media(tmp_path / 'disjoint-source.flv')
    entered, release = Event(), Event()
    started, capture_release = [Event(), Event()], Event()
    original_hash = RecoveryNativeProof._hash
    def paused(held, **options):
        if not entered.is_set():
            entered.set()
            assert release.wait(20), 'fixture recovery barrier expired'
        return original_hash(held, **options)
    monkeypatch.setattr(RecoveryNativeProof, '_hash', staticmethod(paused))
    adapters = [case['adapter']]
    try:
        with ThreadPoolExecutor(max_workers=3) as pool:
            recovery = pool.submit(owner.recover_prepared_release, case['session'], case['token'])
            assert entered.wait(20)
            def capture(index):
                bridge = reserve(owner, 'disjoint-' + str(index), room=str(500 + index),
                                 creator='example.creator.' + str(index))
                def source(_, raw):
                    started[index].set()
                    assert capture_release.wait(8)
                    raw.write(data)
                    yield from iter_tags((data,))
                assert bridge.run(**observations(data, room=str(500 + index), source=source)).phase == 'queued'
                return bridge, owner.journal.session(bridge.intent.session_id)
            captures = [pool.submit(capture, i) for i in range(2)]
            progressed = True
            results = []
            try:
                assert all(event.wait(8) for event in started)
                assert len(owner.journal.status()['bindings']) == 2
                assert len(owner.journal.status()['units']) == 3
                capture_release.set()
                for call in captures:
                    results.append(call.result(timeout=8))
                assert not recovery.done()
                with pytest.raises(JournalError):
                    owner.close()
                competitor = adapter_for(owner, managed_process)
                adapters.append(competitor)
                assert competitor.run() is None
            except TimeoutError:
                progressed = False
            finally:
                capture_release.set()
                release.set()
            assert progressed, 'both disjoint captures must hand off before recovery finishes'
            assert recovery.result(timeout=20)['state'] == 'released'
        after = hashes(owner.root)
        assert all(after[path] == value for path, value in before.items())
        for bridge, original in results:
            current = owner.journal.session(bridge.intent.session_id)
            assert all(current[key] == original[key] for key in ('intent', 'seal', 'seal_hash', 'generation'))
            assert Path(bridge.intent.parts_path).exists() and bridge.intent.raw_copy
        assert len(owner.journal.status()['units']) == 2
        next_adapter = adapter_for(owner, managed_process)
        adapters.append(next_adapter)
        first = min(results, key=lambda value: value[1]['task']['queue_order'])
        assert next_adapter.run()['session_id'] == first[1]['id']
    finally:
        capture_release.set()
        release.set()
        monkeypatch.undo()
        for adapter in adapters:
            independent_cleanup(adapter)
        owner.close()


@pytest.mark.parametrize('namespace', ['root', 'parts', 'scratch'])
def test_shared_root_children_are_allowed_but_attempt_inventories_remain_exact(
        tmp_path, managed_process, namespace):
    owner = authority(tmp_path)
    case = prepared_success(owner, tmp_path, managed_process)
    try:
        def fault(point):
            if point == 'after_recovery_proof':
                parent = {'root': owner.root, 'parts': Path(case['bridge'].intent.parts_path),
                          'scratch': case['adapter'].coordinator.scratch.path}[namespace]
                (parent / 'unrelated-child').mkdir()
        if namespace == 'root':
            assert owner.recover_prepared_release(case['session'], case['token'], fault=fault)['state'] == 'released'
        else:
            with pytest.raises(JournalError, match='namespace changed'):
                owner.recover_prepared_release(case['session'], case['token'], fault=fault)
            assert len(owner.journal.status()['units']) == 1
    finally:
        independent_cleanup(case['adapter'])
        owner.close()


def test_cancel_close_competing_recovery_and_thread_fence_during_native_hash(
        tmp_path, managed_process, monkeypatch):
    owner = authority(tmp_path)
    case = prepared_success(owner, tmp_path, managed_process)
    before = hashes(owner.root)
    entered, release, competing = Event(), Event(), Event()
    read, reads = os.read, []
    first_owner = []
    def paused(fd, size):
        active = owner._release_recovery
        output = active.objects.get('scratch:candidate.mp4') if active else None
        if output is not None and output.fd == fd:
            reads.append(active)
            if not entered.is_set():
                first_owner.append(active)
                entered.set()
                assert release.wait(15), 'hash fixture barrier expired'
        return read(fd, size)
    monkeypatch.setattr(os, 'read', paused)
    try:
        with ThreadPoolExecutor(max_workers=3) as pool:
            recovery = pool.submit(owner.recover_prepared_release, case['session'], case['token'])
            assert entered.wait(15)
            active = first_owner[0]
            def competitor():
                competing.set()
                return owner.recover_prepared_release(case['session'], case['token'])
            repeat = pool.submit(competitor)
            assert competing.wait(2) and not repeat.done()
            close = pool.submit(owner.close)
            with pytest.raises(JournalError, match='active recovery'):
                close.result(timeout=2)
            # Even a copied current call tuple cannot authorize another thread.
            with owner.lock:
                args = [case['token'], active.generation, active.authority_id, {}]
                active.call_thread = get_ident()
                active.call_authority = ('record_release_recovery_proof', *args)
                try:
                    with pytest.raises(JournalError, match='current explicit'):
                        owner.journal.record_release_recovery_proof(operation_id(), *args, capability=active)
                finally:
                    active.call_thread = active.call_authority = None
            with pytest.raises(JournalError, match='address'):
                owner.cancel_release_recovery(operation_id(), case['token'])
            cancel = pool.submit(owner.cancel_release_recovery, case['session'], case['token'])
            assert cancel.result(timeout=2) and not recovery.done()
            assert owner.journal.release_recovery(case['token'])['head']['generation'] == 1
            release.set()
            with pytest.raises(JournalError, match='cancelled'):
                recovery.result(timeout=15)
            assert repeat.result(timeout=15)['state'] == 'released'
        assert sum(held is first_owner[0] for held in reads) == 1
        assert owner.journal.release_recovery(case['token'])['head']['generation'] == 2
        assert not owner.cancel_release_recovery(case['session'], case['token'])
        assert owner.journal.status()['units'] == [] and hashes(owner.root) == before
    finally:
        release.set()
        monkeypatch.undo()
        independent_cleanup(case['adapter'])
        owner.close()


@pytest.mark.parametrize('kind', ['record_release_recovery_cleanup', 'settle_release_recovery'])
def test_two_connected_captures_handoff_during_sqlite_cleanup(tmp_path, managed_process, monkeypatch, kind):
    owner = authority(tmp_path)
    case = prepared_success(owner, tmp_path, managed_process)
    data = local_media(tmp_path / 'cleanup-source.flv')
    entered, release = Event(), Event()
    wrapped = inject_transaction(owner.journal, monkeypatch, kind)
    def fault(selected, point):
        if selected == kind and point == 'after_commit':
            close = wrapped[0].close
            def paused():
                assert not wrapped[0].raw.in_transaction
                entered.set()
                assert release.wait(15), 'SQLite cleanup fixture barrier expired'
                close()
            monkeypatch.setattr(wrapped[0], 'close', paused)
    owner.journal._fault = fault
    try:
        with ThreadPoolExecutor(max_workers=3) as pool:
            recovery = pool.submit(owner.recover_prepared_release, case['session'], case['token'])
            assert entered.wait(15)
            def capture(index):
                room = str(700 + index)
                bridge = reserve(owner, 'cleanup-disjoint-' + str(index), room=room,
                                 creator='example.creator.c' + str(index))
                assert bridge.run(**observations(data, room=room)).phase == 'queued'
                return owner.journal.session(bridge.intent.session_id)
            captures = [pool.submit(capture, i) for i in range(2)]
            try:
                rows = [call.result(timeout=6) for call in captures]
                assert not recovery.done()
                assert len(owner.journal.status()['units']) == (3 if kind == 'record_release_recovery_cleanup' else 2)
                assert all(row['intent']['raw_copy'] and row['phase'] == 'queued' for row in rows)
                if kind == 'settle_release_recovery':
                    assert not owner.cancel_release_recovery(case['session'], case['token'])
            finally:
                release.set()
            assert recovery.result(timeout=15)['state'] == 'released'
            assert len(owner.journal.status()['units']) == 2
    finally:
        release.set()
        monkeypatch.undo()
        owner.journal._fault = None
        independent_cleanup(case['adapter'])
        owner.close()
