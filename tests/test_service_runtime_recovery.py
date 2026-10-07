"""Fresh runtime authority around generated successful prepared releases and faults."""

import os
from threading import Event

import pytest

pytestmark = pytest.mark.skipif(os.name != 'nt', reason='native Windows runtime')

from tests.service_runtime_helpers import runtime_case, managed_process, start, wait_for, hashes
from tests.test_journal_settlement_cleanup import inject_transaction


def prepared_runtime(case):
    """Stop a real connected success after cleanup, leaving a queued successor."""
    entered, release = Event(), Event()
    case.releases.append(release)
    first = OSError('interrupted bookkeeping')
    def fault(point):
        if point == 'before_terminal_release':
            entered.set()
            assert release.wait(30)
            raise first
    case.fault = fault
    original = case.build().start_runtime()
    accepted = start(original, 'prepared')
    assert entered.wait(30)
    next_job = start(original, 'next', room='456', raw=False)
    wait_for(lambda: original.journal.session(next_job['session_id'])['phase'] == 'queued')
    token = original.current.coordinator.token
    release.set()
    wait_for(lambda: original.paused == 'finalizer_needs_attention' and original.current is None)
    assert original.shutdown()['complete']
    case.fault = lambda _: None
    return original, accepted, next_job, token, hashes(original.root / 'prepared.parts')


def test_startup_queued_only_is_observational_until_explicit_start(runtime_case):
    case = runtime_case
    original = case.build()
    # Pausing execution does not create fabricated tasks: captures still use H.
    original.paused = 'fixture_processor_paused'
    original.start_runtime()
    accepted = start(original, 'queued')
    wait_for(lambda: original.journal.session(accepted['session_id'])['phase'] == 'queued')
    old = original.journal.session(accepted['session_id'])
    assert original.shutdown()['complete']
    runtime = case.build()
    assert runtime.journal.session(accepted['session_id']) == old
    assert not (runtime.root / 'queued.mp4').exists()
    runtime.start_runtime()
    wait_for(lambda: runtime.session_status(accepted['session_id'])['output_completed'])
    assert not runtime.journal.status()['units']


def test_prepared_startup_checks_storage_then_automatically_finishes_fifo(runtime_case):
    case = runtime_case
    original, accepted, next_job, token, before = prepared_runtime(case)
    case.free = 0
    runtime = case.build().start_runtime()
    wait_for(lambda: runtime.paused == 'low_free_space')
    assert runtime.journal.release_recovery(token) is None
    assert len(runtime.journal.status()['units']) == 2
    assert not runtime.session_status(accepted['session_id'])['output_completed']
    case.free = 100 * 1024**3
    wait_for(lambda: runtime.session_status(next_job['session_id'])['output_completed'])
    assert runtime.journal.release_recovery(token)['head']['generation'] == 1
    assert hashes(runtime.root / 'prepared.parts') == before
    assert not runtime.journal.status()['units']


def test_shutdown_cancels_fresh_recovery_without_refund_then_next_start_recovers(runtime_case):
    case = runtime_case
    original, accepted, next_job, token, before = prepared_runtime(case)
    entered = Event()
    def fault(point):
        if point == 'after_recovery_authority':
            entered.set()
            assert runtime.authority._release_recovery.cancelled.wait(30)
    runtime = case.build(recovery_fault=fault, shutdown_grace=0).start_runtime()
    assert entered.wait(10)
    result = runtime.shutdown()
    assert result['complete'] and not runtime.worker.is_alive()
    assert len(runtime.journal.status()['units']) == 2
    assert runtime.journal.release_recovery(token)['head']['generation'] == 1
    assert hashes(runtime.root / 'prepared.parts') == before
    next_runtime = case.build().start_runtime()
    wait_for(lambda: next_runtime.session_status(next_job['session_id'])['output_completed'])
    assert next_runtime.journal.release_recovery(token)['head']['generation'] == 2
    assert not next_runtime.journal.status()['units']
    assert hashes(next_runtime.root / 'prepared.parts') == before


@pytest.mark.parametrize('lookup', [False, True])
def test_recovery_terminal_ack_loss_preserves_history_and_capacity(runtime_case, monkeypatch, lookup):
    case = runtime_case
    original, accepted, next_job, token, before = prepared_runtime(case)
    journal = original.journal
    first, lost = OSError('recovery terminal acknowledgement'), []
    operation = journal.operation
    def fault(kind, point):
        if kind == 'settle_release_recovery' and point == 'after_commit':
            lost.append(True)
            raise first
    def lookup_operation(identity):
        if lost and not lookup:
            raise OSError('lookup unavailable')
        return operation(identity)
    journal._fault = fault
    monkeypatch.setattr(journal, 'operation', lookup_operation)
    runtime = case.build().start_runtime()
    wait_for(lambda: runtime.session_status(accepted['session_id'])['output_completed'])
    if lookup:
        wait_for(lambda: runtime.session_status(next_job['session_id'])['output_completed'])
    else:
        wait_for(lambda: runtime.paused == 'finalizer_needs_attention')
        assert len(journal.status()['units']) == 1
    assert journal.release_recovery(token)['head']['generation'] == 1
    assert hashes(runtime.root / 'prepared.parts') == before
    assert runtime.shutdown()['complete']
    journal._fault = None
    monkeypatch.setattr(journal, 'operation', operation)
    restart = case.build().start_runtime()
    wait_for(lambda: restart.session_status(next_job['session_id'])['output_completed'])
    assert journal.release_recovery(token)['head']['generation'] == 1
    assert not journal.status()['units']


def test_recovery_unknown_sqlite_close_retains_owning_worker_and_catalog(runtime_case, monkeypatch):
    case = runtime_case
    original, accepted, next_job, token, before = prepared_runtime(case)
    first = OSError('fresh recovery reader close')
    retained = inject_transaction(original.journal, monkeypatch, 'begin_release_recovery', close=first)
    runtime = case.build(shutdown_grace=0).start_runtime()
    wait_for(lambda: runtime.paused == 'finalizer_needs_attention')
    assert runtime.errors[0] is first
    owner = runtime.authority._recovery_owners[token]
    assert owner.has_retained_ownership()
    assert len(runtime.journal.status()['units']) == 2
    result = runtime.shutdown()
    assert not result['complete'] and not result['authority_released']
    assert runtime.worker.is_alive()
    assert hashes(runtime.root / 'prepared.parts') == before
    retained[0].close_error = None
    runtime.cleanup_requested.set()
    runtime.wake.set()
    wait_for(lambda: not owner.has_retained_ownership())
    assert runtime.shutdown()['complete']
    monkeypatch.undo()
    next_runtime = case.build().start_runtime()
    wait_for(lambda: next_runtime.session_status(next_job['session_id'])['output_completed'])
    assert next_runtime.journal.release_recovery(token)['head']['generation'] == 2
    assert not next_runtime.journal.status()['units']
