"""R11 teardown faults on the real connected Windows control transitions."""

import os
import sqlite3

import pytest

from tests.journal_manifest_helpers import completing
from tests.journal_assembly_helpers import managed_process
from tests.journal_publication_helpers import held_hash
from tests.manifest_fence_helpers import inject_selected_fence
from tikrec.journal_manifest import ManifestCompletionError

pytestmark = pytest.mark.skipif(os.name != 'nt', reason='native Windows manifest fences')


@pytest.mark.parametrize('phase,count', [('preserve', 1), ('install', 2)])
@pytest.mark.parametrize('body', ['before', 'after', 'success'])
@pytest.mark.parametrize('cleanup', ['rollback', 'close', 'both'])
def test_connected_native_and_teardown_failures_retain_exact_owners(completing, monkeypatch, phase, count, body, cleanup):
    from tikrec import manifest_completion as module
    adapter, _, original, _, raw = completing
    runner = adapter.coordinator
    primary = OSError('first native transition failure')
    rollback_error, close_error = sqlite3.OperationalError('rollback fault'), sqlite3.OperationalError('close fault')
    retained = inject_selected_fence(runner.journal, monkeypatch, count,
        rollback=rollback_error if cleanup in {'rollback', 'both'} else None,
        close=close_error if cleanup in {'close', 'both'} else None)
    native, calls = module.rename_no_replace, []
    def rename(*args):
        selected = args[2] == ('session.json' if phase == 'install' else runner.manifest_owner.history.name)
        if selected:
            calls.append(args[2])
            if body == 'before':
                raise primary
        result = native(*args)
        if selected and body == 'after':
            raise primary
        return result
    monkeypatch.setattr(module, 'rename_no_replace', rename)
    try:
        with pytest.raises(ManifestCompletionError) as caught:
            adapter.run()
        expected = primary if body != 'success' else rollback_error if cleanup != 'close' else close_error
        assert caught.value.original is expected and adapter.error is expected
        cap, wrapped = adapter.capability, retained[0]
        owner = cap.fence_owner
        assert expected.manifest_fence_owner is owner
        assert wrapped.calls[-2:] == ['rollback', 'close']
        diagnostics = [error for _, error in owner.errors]
        assert all(any(e is error for e in caught.value.diagnostics) for error in diagnostics)
        assert caught.value.diagnostics_dropped == 0
        assert owner.connection is (wrapped if cleanup != 'rollback' else None)
        assert cap.predecessor.read_control() == raw and cap.predecessor.handle and cap.stage.handle
        candidate = runner.journal.scratch(runner.token)['candidate']
        assert held_hash(runner.scratch.artifacts['candidate.mp4']) == candidate['sha256']
        record = runner.journal.manifest_completion(runner.token)
        assert [s['phase'] for s in record['steps']] == (['staged'] if phase == 'preserve' else ['staged', 'preserved'])
        assert runner.journal.session(original['id'])['task']['state'] == 'running'
        assert runner.journal.status()['units'] and runner.guard.retained
        assert not adapter.close()
        evidence = runner.cleanup_evidence()['manifest']['fence']
        assert evidence['connection_retained'] is (cleanup != 'rollback')
        assert not runner.cleanup_evidence()['cleanup_complete']
        before = len(calls)
        wrapped.rollback_error = wrapped.close_error = None
        assert not adapter.close()  # Reader cleanup confirms; native/media pins stay.
        assert owner.connection is None and runner.cleanup_evidence()['manifest']['fence']['cleanup_complete']
        assert len(calls) == before == 1 and adapter.error is expected
        with pytest.raises(Exception):
            cap.complete()
    finally:
        for wrapped in retained:
            wrapped.raw.close()  # Independently dispose even on the unchanged baseline.


@pytest.mark.parametrize('completing', [True], indirect=True, ids=['libx264'])
@pytest.mark.parametrize('count', [0, 2])
def test_libx264_successful_native_body_failed_teardown_never_records_success(completing, monkeypatch, count):
    adapter, _, _, _, raw = completing
    runner = adapter.coordinator
    rollback_error, close_error = OSError('rollback first'), OSError('close second')
    retained = inject_selected_fence(runner.journal, monkeypatch, count, rollback=rollback_error, close=close_error)
    try:
        with pytest.raises(ManifestCompletionError) as caught:
            adapter.run()
        assert caught.value.original is rollback_error
        cap, wrapped = adapter.capability, retained[0]
        assert cap.fence_owner.connection is wrapped
        assert cap.predecessor.read_control() == raw
        assert [s['phase'] for s in runner.journal.manifest_completion(runner.token)['steps']] == ([] if count == 0 else ['staged', 'preserved'])
        assert cap.installed is (count == 2) and cap.stage.handle and runner.guard.retained
        wrapped.rollback_error = wrapped.close_error = None
        assert not adapter.close() and cap.fence_owner.connection is None
    finally:
        for wrapped in retained:
            wrapped.raw.close()


@pytest.mark.parametrize('failed_close', [False, True])
def test_connected_catalog_reader_cleanup_unblocks_same_disjoint_writer(completing, monkeypatch, failed_close):
    from tikrec import manifest_completion as module
    adapter, _, _, _, _ = completing
    runner, primary = adapter.coordinator, OSError('native preserve refused')
    retained = inject_selected_fence(runner.journal, monkeypatch, 1,
        rollback=OSError('rollback unavailable'), close=OSError('close unavailable') if failed_close else None)
    monkeypatch.setattr(module, 'rename_no_replace', lambda *_args: (_ for _ in ()).throw(primary))
    writer = None
    try:
        with pytest.raises(ManifestCompletionError) as caught:
            adapter.run()
        assert caught.value.original is primary
        wrapped, owner = retained[0], adapter.capability.fence_owner
        writer = sqlite3.connect(runner.journal.path, isolation_level=None, timeout=0.05)
        before = writer.execute('SELECT * FROM bindings WHERE slot=2').fetchone()
        writer.execute('BEGIN IMMEDIATE')
        # An idempotent fixture-only write requires exclusive commit without changing claims.
        writer.execute('UPDATE bindings SET generation=generation WHERE slot=2')
        if failed_close:
            with pytest.raises(sqlite3.OperationalError, match='locked'):
                writer.commit()
            assert writer.in_transaction and owner.connection is wrapped
            wrapped.rollback_error = wrapped.close_error = None
            owner.cleanup()
        writer.commit()  # Exactly the same pending UPDATE, never a second execution.
        assert writer.total_changes == 1 and writer.execute('SELECT * FROM bindings WHERE slot=2').fetchone() == before
        assert owner.connection is None and not adapter.close()
    finally:
        if writer is not None:
            writer.close()
        for wrapped in retained:
            wrapped.raw.close()
