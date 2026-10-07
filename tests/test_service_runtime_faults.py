"""Integrated failures preserve terminal accounting and exact native/SQLite owners."""

import os

import pytest

pytestmark = pytest.mark.skipif(os.name != 'nt', reason='native Windows runtime')

from tests.service_runtime_helpers import runtime_case, managed_process, start, wait_for, hashes, preserved
from tests.test_journal_settlement_cleanup import inject_transaction


@pytest.mark.parametrize('lookup', [False, True])
def test_terminal_acknowledgement_loss_never_reverts_or_double_returns(runtime_case, monkeypatch, lookup):
    case = runtime_case
    runtime = case.build().start_runtime()
    first = OSError('terminal acknowledgement lost')
    original = runtime.journal.operation
    calls = []
    def fault(kind, point):
        if kind == 'settle_owned_success' and point == 'after_commit':
            raise first
    def operation(identity):
        calls.append(identity)
        if not lookup:
            raise OSError('lookup unavailable')
        return original(identity)
    runtime.journal._fault = fault
    monkeypatch.setattr(runtime.journal, 'operation', operation)
    accepted = start(runtime, 'one')
    wait_for(lambda: runtime.session_status(accepted['session_id'])['output_completed'])
    wait_for(lambda: runtime.current is None)
    assert not runtime.journal.status()['units'] and len(calls) == 1
    assert runtime.journal._read(lambda db: db.execute('SELECT count(*) FROM release_results').fetchone()[0]) == 1
    assert runtime.shutdown()['complete']
    runtime.journal._fault = None
    monkeypatch.setattr(runtime.journal, 'operation', original)
    restarted = case.build().start_runtime()
    assert restarted.session_status(accepted['session_id'])['output_completed']
    assert not restarted.journal.status()['units']
    assert restarted.journal._read(lambda db: db.execute('SELECT count(*) FROM release_results').fetchone()[0]) == 1


def test_terminal_reporting_failure_keeps_completed_status(runtime_case):
    case = runtime_case
    first = OSError('local completion reporting failed')
    def fault(point):
        if point == 'after_terminal_release':
            raise first
    case.fault = fault
    runtime = case.build().start_runtime()
    accepted = start(runtime, 'one')
    wait_for(lambda: runtime.paused == 'finalizer_needs_attention')
    assert runtime.session_status(accepted['session_id'])['output_completed']
    assert runtime.journal.status()['units'] == []
    assert runtime.errors[0].original is first
    assert runtime.shutdown()['complete']


@pytest.mark.parametrize('resource', ['native', 'sqlite'])
def test_incomplete_release_cleanup_stays_pinned_and_owned(runtime_case, monkeypatch, resource):
    case = runtime_case
    runtime = case.build(shutdown_grace=0).start_runtime()
    first = OSError('exact cleanup unavailable')
    retained = []
    if resource == 'sqlite':
        retained = inject_transaction(runtime.journal, monkeypatch, 'settle_owned_success', close=first)
    else:
        def fault(point):
            if point == 'after_release_preparation':
                held = runtime.current.coordinator.scratch.artifacts['candidate.mp4']
                retained.append(held)
                monkeypatch.setattr(held, 'close', lambda: (_ for _ in ()).throw(first))
        case.fault = fault
    accepted = start(runtime, 'one')
    wait_for(lambda: runtime.paused == 'finalizer_needs_attention')
    adapter = runtime.current
    assert adapter is not None and retained
    terminal = resource == 'sqlite'
    assert runtime.session_status(accepted['session_id'])['output_completed'] is terminal
    assert len(runtime.journal.status()['units']) == (0 if terminal else 1)
    if terminal:
        assert any(reader.connection is retained[0] for reader in adapter.capability.readers)
    else:
        assert retained[0].handle is not None
        assert runtime.journal.settlement(adapter.coordinator.token)['state'] == 'cleanup_incomplete'
    result = runtime.shutdown()
    assert not result['complete'] and not result['authority_released']
    assert runtime.worker.is_alive() and not runtime.worker.daemon
    assert adapter.coordinator.token in runtime.authority._attempts
    if terminal:
        retained[0].close_error = None
        # Cleanup is requested again on the original worker, never the test thread.
        runtime.cleanup_requested.set()
        runtime.wake.set()
        wait_for(lambda: runtime.current is None)
        assert runtime.shutdown()['complete']
