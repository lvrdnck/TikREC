"""Runtime control readers retain exact SQLite ownership without changing journal guards."""

import os
from threading import get_ident

import pytest

pytestmark = pytest.mark.skipif(os.name != 'nt', reason='native Windows runtime')

from tests.service_runtime_helpers import runtime_case, managed_process, start, wait_for
from tests.manifest_fence_helpers import ConnectionFaults
from tikrec.recording import RecordingBusy


@pytest.mark.parametrize('thread', ['caller', 'worker'])
def test_control_reader_close_fault_blocks_exit_until_original_thread_cleanup(runtime_case, monkeypatch, thread):
    case = runtime_case
    runtime = case.build(shutdown_grace=0)
    original, retained = runtime.connections.original, []
    first = OSError('control reader close unavailable')
    caller = get_ident()
    def once():
        connection = original()
        if not retained and (thread == 'worker' or get_ident() == caller):
            connection = ConnectionFaults(connection, close=first)
            retained.append(connection)
        return connection
    monkeypatch.setattr(runtime.connections, 'original', once)
    if thread == 'caller':
        runtime.paused = 'fixture_worker_paused'
        value = runtime.health()
        assert value['active_count'] is None and value['available_slots'] == 0
        assert runtime.errors[0] is first
    runtime.start_runtime()
    if thread == 'worker':
        wait_for(lambda: runtime.paused == 'finalizer_needs_attention')
        assert runtime.errors[0] is first
    assert runtime.connections.failed(runtime)
    assert runtime.health()['admission_reason'] == 'catalog_cleanup_needs_attention'
    with pytest.raises(RecordingBusy, match='catalog_cleanup_needs_attention'):
        start(runtime, 'refused')
    result = runtime.shutdown()
    assert not result['complete'] and not result['authority_released']
    assert runtime.worker.is_alive() and len(runtime.connections.connections) == 1
    # No repeated status read creates another unknown owner while paused.
    assert runtime.health()['finalization']['outstanding_units'] is None
    retained[0].close_error = None
    assert runtime.shutdown()['complete']
    assert not runtime.connections.has_ownership()
    assert not runtime.worker.is_alive()
    assert runtime.journal.status()['units'] == []
    monkeypatch.undo()
    fresh = case.build().start_runtime()
    accepted = start(fresh, 'healthy')
    wait_for(lambda: fresh.session_status(accepted['session_id'])['output_completed'])


def test_generic_control_uncertainty_cannot_release_running_success(runtime_case, monkeypatch):
    from threading import Event
    case = runtime_case
    entered, release = Event(), Event()
    case.releases.append(release)
    def fault(point):
        if point == 'before_release_preparation':
            entered.set()
            assert release.wait(30)
    case.fault = fault
    runtime = case.build(shutdown_grace=0).start_runtime()
    accepted = start(runtime, 'one')
    assert entered.wait(30)
    original, retained = runtime.connections.original, []
    caller = get_ident()
    def once():
        connection = original()
        if get_ident() == caller and not retained:
            connection = ConnectionFaults(connection, close=OSError('unconfirmed caller reader'))
            retained.append(connection)
        return connection
    monkeypatch.setattr(runtime.connections, 'original', once)
    assert runtime.health()['available_slots'] == 0
    release.set()
    wait_for(lambda: runtime.paused == 'finalizer_needs_attention')
    assert len(runtime.journal.status()['units']) == 1
    assert not runtime.session_status(accepted['session_id'])['output_completed']
    assert runtime.journal.settlement(runtime.current.coordinator.token) is None
    retained[0].close_error = None
    # Earlier unfinished phases remain unsupported and pinned after local cleanup.
    runtime.shutdown()
    assert len(runtime.journal.status()['units']) == 1


def test_new_reader_is_fenced_during_final_catalog_close(runtime_case, monkeypatch):
    from threading import Event, Thread
    case = runtime_case
    runtime = case.build().start_runtime()
    accepted = start(runtime, 'one')
    wait_for(lambda: runtime.session_status(accepted['session_id'])['output_completed'])
    entered, release = Event(), Event()
    held = runtime.authority.catalog
    original = held.close
    def close():
        entered.set()
        assert release.wait(15)
        original()
    monkeypatch.setattr(held, 'close', close)
    result = []
    worker = Thread(target=lambda: result.append(runtime.shutdown()), daemon=False)
    worker.start()
    try:
        assert entered.wait(10)
        assert runtime.connections.closing
        assert not runtime.connections.has_ownership()
        assert runtime.health()['available_slots'] == 0
        assert not runtime.connections.has_ownership()
    finally:
        release.set()
        worker.join(15)
    assert not worker.is_alive() and result[0]['complete']
    assert not runtime.connections.enabled
    assert runtime.session_status(accepted['session_id'])['output_completed']
