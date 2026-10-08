"""Owned integrated shutdown, actual children and deliberately retained failures."""

import os
from threading import Event, Thread

import pytest

pytestmark = pytest.mark.skipif(os.name != 'nt', reason='native Windows runtime')

from tests.service_runtime_helpers import runtime_case, managed_process, start, wait_for
from tikrec.recording import RecordingBusy


def test_shutdown_two_captures_running_and_queued_does_not_drain(runtime_case):
    case = runtime_case
    entered = Event()
    runtime = case.build().start_runtime()
    def fault(point):
        if point == 'before_terminal_release':
            entered.set()
            assert runtime.stopping.wait(30)
    case.fault = fault
    old = start(runtime, 'old')
    assert entered.wait(30)
    queued = start(runtime, 'queued', room='456')
    wait_for(lambda: runtime.journal.session(queued['session_id'])['phase'] == 'queued')
    captures = []
    for name, room, creator in [('a', '789', 'example.creator'), ('b', '987', 'example.second')]:
        ready, _ = case.hold(name)
        case.cooperative.add(name)
        accepted = start(runtime, name, room=room, creator=creator)
        assert ready.wait(10)
        captures.append(accepted)
    assert len(runtime.journal.status()['units']) == 4
    result = runtime.shutdown()
    assert result['complete'] and result['authority_released']
    assert not runtime.worker.is_alive() and not runtime.worker.daemon
    assert runtime.session_status(old['session_id'])['output_completed']
    assert runtime.journal.session(queued['session_id'])['phase'] == 'queued'
    assert len(runtime.journal.status()['units']) == 3
    assert runtime.health()['active_count'] == 0
    for accepted in captures:
        assert runtime.journal.session(accepted['session_id'])['phase'] == 'queued'
        assert not runtime.capture_callback(accepted['session_id'], accepted['generation'], 'state', 'capturing')
    with pytest.raises(RecordingBusy):
        start(runtime, 'late', room='654')
    # An explicit new runtime, rather than shutdown, consumes the retained FIFO.
    case.fault = lambda _: None
    restarted = case.build().start_runtime()
    wait_for(lambda: not restarted.journal.status()['units'])
    assert all(row['phase'] == 'completed' for row in restarted.journal.history())


@pytest.mark.parametrize('guarded', [False, True])
def test_zero_grace_cancels_actual_assembly_child_and_reports_retained_protection(runtime_case, guarded):
    case = runtime_case
    entered = Event()
    runtime = case.build(shutdown_grace=0, authority_cleanup_guards=guarded).start_runtime()
    create = runtime.settlement_options['process_factory']
    children = []
    def process(sid, token):
        owner = create(sid, token)
        original = owner._fault
        def fault(point):
            original(point)
            if point == 'after_resume' and runtime.current.coordinator.children[-1]['intent']['phase'] == 'assembly':
                children.append(owner)
                entered.set()
                assert runtime.current.coordinator.cancelled.wait(30)
        owner._fault = fault
        return owner
    runtime.settlement_options['process_factory'] = process
    accepted = start(runtime, 'cancel')
    assert entered.wait(30)
    result = runtime.shutdown()
    assert not result['complete'] and not result['authority_released']
    assert runtime.closed and runtime.current is not None
    assert runtime.current.coordinator.cancelled.is_set()
    assert children and all(c.evidence().state == 'confirmed_exited' and c.closed for c in children)
    assert len(runtime.journal.status()['units']) == 1
    assert not runtime.session_status(accepted['session_id'])['output_completed']
    assert runtime.worker.is_alive() and not runtime.worker.daemon
    # Fixture cleanup is independent and explicitly joins this retained worker.


@pytest.mark.parametrize('stage', ['construct', 'start'])
def test_finalizer_launch_failure_never_claims_and_can_release_catalog(runtime_case, stage):
    case = runtime_case
    first = OSError('worker launch failure')
    def factory(**options):
        if stage == 'construct':
            raise first
        worker = Thread(**options)
        worker.start = lambda: (_ for _ in ()).throw(first)
        return worker
    runtime = case.build(thread_factory=factory)
    with pytest.raises(OSError) as error:
        runtime.start_runtime()
    assert error.value is first and runtime.errors[0] is first
    assert runtime.paused == 'worker_launch_failed' and runtime.worker is None
    assert not runtime.journal.history()
    assert runtime.shutdown()['complete']


def test_capture_post_h_close_failure_retains_authority_and_blocks_unbounded_owners(runtime_case, monkeypatch):
    case = runtime_case
    ready, release = case.hold('close')
    runtime = case.build().start_runtime()
    accepted = start(runtime, 'close')
    assert ready.wait(10)
    bridge = runtime.captures[accepted['session_id']]['bridge']
    first = OSError('capture lease close unconfirmed')
    close = bridge.lease.close
    def failed():
        close()
        raise first
    monkeypatch.setattr(bridge.lease, 'close', failed)
    release.set()
    wait_for(lambda: runtime.session_status(accepted['session_id'])['output_completed'])
    assert runtime.journal.status()['units'] == []
    assert first in runtime.errors
    assert runtime.health()['admission_reason'] == 'capture_cleanup_needs_attention'
    with pytest.raises(RecordingBusy, match='capture_cleanup_needs_attention'):
        start(runtime, 'refused', room='456')
    result = runtime.shutdown()
    assert not result['complete'] and not result['authority_released']
    assert result['captures_joined'] and result['finalizer_joined']


def test_stop_racing_confirmed_h_is_closed_capture_noop(runtime_case, monkeypatch):
    case = runtime_case
    ready, release = case.hold('one')
    runtime = case.build().start_runtime()
    accepted = start(runtime, 'one')
    assert ready.wait(10)
    sealing, allow_h = Event(), Event()
    case.releases.append(allow_h)
    def before_h(point):
        if point == 'before_inventory':
            sealing.set()
            assert allow_h.wait(30)
    runtime.captures[accepted['session_id']]['bridge']._fault = before_h
    release.set()
    assert sealing.wait(10)
    from tikrec import service_runtime_status as module
    original = module.session_status
    once = []
    def after_snapshot(value, sid):
        snapshot = original(value, sid)
        if not once:
            once.append(True)
            allow_h.set()
            # The stop caller holds its own status lock; H is committed independently.
            wait_for(lambda: value.journal.session(sid)['phase'] in {'queued', 'running', 'completed'})
        return snapshot
    monkeypatch.setattr(module, 'session_status', after_snapshot)
    result = runtime.stop(accepted['session_id'])
    assert result['stop_result'] == 'capture_already_closed'
    assert not runtime.journal.session(accepted['session_id'])['stop']


def test_catalog_close_failure_cannot_be_hidden_by_empty_exit_stack(runtime_case, monkeypatch):
    runtime = runtime_case.build().start_runtime()
    held = runtime.authority.catalog
    first = OSError('catalog close unavailable')
    monkeypatch.setattr(held, 'close', lambda: (_ for _ in ()).throw(first))
    assert not runtime.shutdown()['complete']
    assert held.handle is not None and runtime.errors[0] is first
    assert not runtime.shutdown()['complete']
    assert not runtime.authority_closed and not runtime.worker.is_alive()
    monkeypatch.undo()
    # Explicit known-object fixture close, never reconstruction from old receipts.
    held.close()
    assert runtime.shutdown()['complete']


def test_capture_real_windows_close_error_is_not_python_closed_proof(runtime_case):
    import ctypes
    import msvcrt
    from ctypes import wintypes
    from tests.test_release_recovery_windows_close import protection
    case = runtime_case
    ready, release = case.hold('protected')
    runtime = case.build().start_runtime()
    accepted = start(runtime, 'protected')
    assert ready.wait(10)
    lease = runtime.captures[accepted['session_id']]['bridge'].lease
    original = msvcrt.get_osfhandle(lease.handle.fileno())
    api = ctypes.WinDLL('kernel32', use_last_error=True)
    api.CloseHandle.argtypes, api.CloseHandle.restype = (wintypes.HANDLE,), wintypes.BOOL
    protection(original, True)
    try:
        release.set()
        wait_for(lambda: runtime.captures[accepted['session_id']]['done'])
        assert lease.closed and lease.handle.closed and lease.cleanup_errors
        wait_for(lambda: runtime.session_status(accepted['session_id'])['output_completed'])
        assert not runtime.shutdown()['complete']
        assert runtime.health()['admission_reason'] == 'capture_cleanup_needs_attention'
    finally:
        # Windows close protection guarantees this fixture's exact handle survived.
        protection(original, False)
        assert api.CloseHandle(original)
