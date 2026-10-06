"""Exact cleanup owners, independent close faults, R11 semantics and SQLite threads."""

import os
import sqlite3
from threading import Thread

import pytest

from tests.journal_settlement_helpers import settling
from tests.journal_assembly_helpers import managed_process
from tests.manifest_fence_helpers import ConnectionFaults
from tikrec.journal_settlement import SettlementError

pytestmark = pytest.mark.skipif(os.name != 'nt', reason='native Windows exact cleanup')


@pytest.mark.parametrize('resource', ['output', 'workspace', 'source', 'successor', 'lease'])
@pytest.mark.parametrize('after_close', [False, True])
def test_native_close_failure_keeps_capacity_and_attempts_other_safe_cleanup(settling, monkeypatch, resource, after_close):
    adapter, _, original, _, _ = settling
    runner, owners = adapter.coordinator, []
    first = OSError('exact close unconfirmed')
    def fault(point):
        if point != 'after_release_preparation':
            return
        held = {'output': runner.scratch.artifacts['candidate.mp4'], 'workspace': runner.scratch.workspace,
            'source': runner.guard.files[0], 'successor': runner.manifest_owner.stage,
            'lease': runner.guard.lifecycle}[resource]
        owners.append(held)
        close = held.close
        def failed():
            if after_close:
                close()
            raise first
        monkeypatch.setattr(held, 'close', failed)
    runner._fault = fault
    with pytest.raises(SettlementError) as error:
        adapter.run()
    assert error.value.original is first and first in error.value.diagnostics
    cap = adapter.capability
    assert not cap.cleanup_result['cleanup_complete']
    assert sum(not r['closed'] for r in cap.cleanup_result['resources']) == 1
    assert runner.journal.settlement(runner.token)['state'] == 'cleanup_incomplete'
    current = runner.journal.session(original['id'])
    assert current['task']['state'] == 'running' and current['artifacts'] == original['artifacts']
    assert len(runner.journal.status()['units']) == 1
    assert not adapter.close()
    assert cap.first_cleanup_error is first and any(owner is owners[0] for _, owner in cap.objects)


def test_primary_and_secondary_cleanup_failures_stay_separate(settling, monkeypatch):
    adapter, _, _, _, _ = settling
    runner = adapter.coordinator
    first, second = OSError('first resource close'), OSError('second resource close')
    def fail(error):
        raise error
    def fault(point):
        if point == 'after_release_preparation':
            monkeypatch.setattr(runner.guard.handles[0], 'close', lambda: fail(first))
            monkeypatch.setattr(runner.scratch.workspace, 'close', lambda: fail(second))
    runner._fault = fault
    with pytest.raises(SettlementError) as error:
        adapter.run()
    assert error.value.original is first
    assert first in error.value.diagnostics and second in error.value.diagnostics
    assert sum(not r['closed'] for r in adapter.capability.cleanup_result['resources']) == 2
    assert runner.manifest_owner.stage.handle is None


def inject_transaction(journal, monkeypatch, kind, **faults):
    """Wrap exactly one release transaction; other journal readers stay native."""
    connect, method, retained = journal._connect, getattr(journal, kind), []
    class Wrapped(ConnectionFaults):
        def commit(self):
            self.calls.append('commit')
            return self.raw.commit()
    def selected(*args, **kwargs):
        def once():
            monkeypatch.setattr(journal, '_connect', connect)
            wrapped = Wrapped(connect(), **faults)
            retained.append(wrapped)
            return wrapped
        monkeypatch.setattr(journal, '_connect', once)
        return method(*args, **kwargs)
    monkeypatch.setattr(journal, kind, selected)
    return retained


@pytest.mark.parametrize('kind', ['prepare_release', 'record_release_cleanup', 'settle_owned_success'])
@pytest.mark.parametrize('failures', ['rollback', 'close', 'both'])
def test_release_sqlite_cleanup_preserves_exact_connection_and_terminal_commit(settling, monkeypatch, kind, failures):
    adapter, _, original, _, _ = settling
    runner = adapter.coordinator
    rollback, close = sqlite3.OperationalError('rollback fault'), sqlite3.OperationalError('close fault')
    wrapped = inject_transaction(runner.journal, monkeypatch, kind,
        rollback=rollback if failures != 'close' else None, close=close if failures != 'rollback' else None)
    with pytest.raises(SettlementError) as error:
        adapter.run()
    assert error.value.original is (rollback if failures != 'close' else close)
    assert wrapped[0].calls[-2:] == ['rollback', 'close']
    owner = adapter.capability.readers[-1]
    assert (owner.connection is wrapped[0]) == (failures != 'rollback')
    terminal = kind == 'settle_owned_success'
    assert runner.journal.session(original['id'])['task']['state'] == ('completed' if terminal else 'running')
    assert len(runner.journal.status()['units']) == (0 if terminal else 1)
    if terminal:
        assert adapter.cleanup_evidence()['state'] == 'released'
    wrong = []
    if owner.connection is not None:
        wrapped[0].rollback_error, wrapped[0].close_error = None, None
        worker = Thread(target=lambda: wrong.append(owner.cleanup()))
        worker.start()
        worker.join(5)
        assert not worker.is_alive() and owner.connection is wrapped[0]
        assert any(isinstance(e, sqlite3.ProgrammingError) for _, e in wrong[0])
        assert owner.cleanup() == () and owner.connection is None


@pytest.mark.parametrize('failures', ['rollback', 'close', 'both'])
def test_release_body_error_stays_primary_through_connection_cleanup(settling, monkeypatch, failures):
    adapter, _, _, _, _ = settling
    runner = adapter.coordinator
    primary = RuntimeError('first transaction body error')
    inject_transaction(runner.journal, monkeypatch, 'prepare_release',
        rollback=OSError('rollback secondary') if failures != 'close' else None,
        close=OSError('close secondary') if failures != 'rollback' else None)
    def fault(kind, point):
        if kind == 'prepare_release' and point == 'before_commit':
            raise primary
    runner.journal._fault = fault
    with pytest.raises(SettlementError) as error:
        adapter.run()
    assert error.value.original is primary
    owner = primary.manifest_fence_owner
    assert owner is adapter.capability.readers[0]
    assert len(owner.errors) == (2 if failures == 'both' else 1)
    if owner.connection is not None:
        # Pending rollback must be completed on the same exact disposable connection.
        owner.connection.rollback_error, owner.connection.close_error = None, None
        assert owner.cleanup() == ()
    assert runner.journal.settlement(runner.token) is None
    assert runner.journal.status()['units']


@pytest.mark.parametrize('after', [False, True])
def test_new_success_path_preserves_r11_native_body_error_and_exact_reader(settling, monkeypatch, after):
    from tests.manifest_fence_helpers import inject_selected_fence
    from tikrec import manifest_completion as module
    adapter, _, _, _, _ = settling
    runner = adapter.coordinator
    first, rollback, close = OSError('first native transition error'), OSError('rollback'), OSError('close')
    retained = inject_selected_fence(runner.journal, monkeypatch, 2, rollback=rollback, close=close)
    native = module.rename_no_replace
    def failed(*args):
        if args[-1] == 'session.json':
            if after:
                native(*args)
            raise first
        return native(*args)
    monkeypatch.setattr(module, 'rename_no_replace', failed)
    with pytest.raises(SettlementError) as error:
        adapter.run()
    assert error.value.original is first
    cap = runner.manifest_owner
    assert cap.fence_owner.connection is retained[0]
    assert rollback in error.value.diagnostics and close in error.value.diagnostics
    assert runner.journal.settlement(runner.token) is None
    assert runner.journal.status()['units']
    retained[0].rollback_error, retained[0].close_error = None, None
    assert cap.cleanup_fence()
