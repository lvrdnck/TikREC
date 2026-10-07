"""Real committed H must wait for incompatible local proof handles to retire."""

import os
from threading import Event

import pytest

pytestmark = pytest.mark.skipif(os.name != 'nt', reason='native Windows runtime')

from tests.service_runtime_helpers import runtime_case, managed_process, start, wait_for


def test_confirmed_h_poll_does_not_consume_attempt_before_native_teardown(runtime_case, monkeypatch):
    from tikrec import service_runtime_worker as worker
    case = runtime_case
    source_ready, source_release = case.hold('old')
    confirmed, close_allowed, polled = Event(), Event(), Event()
    case.releases.append(close_allowed)
    runtime = case.build().start_runtime()
    accepted = start(runtime, 'old')
    assert source_ready.wait(10)
    sid = accepted['session_id']
    bridge = runtime.captures[sid]['bridge']
    def handoff(point):
        if point == 'confirmed_h':
            confirmed.set()
            assert close_allowed.wait(45), 'exact H-proof close barrier not released'
    bridge._fault = handoff
    original = worker.process_once
    def observe(value, startup):
        try:
            return original(value, startup)
        finally:
            if value is runtime and confirmed.is_set():
                polled.set()
    monkeypatch.setattr(worker, 'process_once', observe)
    # Both hints can be missed; the actual worker's bounded durable poll remains.
    monkeypatch.setattr(runtime.wake, 'set', lambda: None)
    runtime.notify = lambda _: (_ for _ in ()).throw(OSError('missed H hint'))
    source_release.set()
    assert confirmed.wait(30) and polled.wait(10)
    try:
        row = runtime.journal.session(sid)
        assert row['phase'] == 'queued', row
        assert runtime.current is None and not runtime.authority._attempts
        assert not runtime.captures[sid]['done']
        assert runtime.health()['active_count'] == 0
        replacements = []
        for name, room, creator in [('new-a', '456', 'example.creator'), ('new-b', '789', 'example.second')]:
            entered, _ = case.hold(name)
            replacements.append(start(runtime, name, room=room, creator=creator))
            assert entered.wait(10)
        assert runtime.health()['active_count'] == 2
        close_allowed.set()
        wait_for(lambda: runtime.session_status(sid)['output_completed'])
        assert runtime.paused is None
        assert len(runtime.journal.status()['units']) == 2
        assert all(runtime.journal.session(r['session_id'])['phase'] == 'capturing' for r in replacements)
    finally:
        close_allowed.set()


def test_oldest_h_barrier_prevents_leapfrogging_ready_libx264(runtime_case, monkeypatch):
    from tikrec import service_runtime_worker as worker
    case = runtime_case
    source_ready, source_release = case.hold('first')
    confirmed, release, second_polled = Event(), Event(), Event()
    case.releases.append(release)
    runtime = case.build().start_runtime()
    first = start(runtime, 'first')
    assert source_ready.wait(10)
    def fault(point):
        if point == 'confirmed_h':
            confirmed.set()
            assert release.wait(45)
    runtime.captures[first['session_id']]['bridge']._fault = fault
    source_release.set()
    assert confirmed.wait(30)
    case.different.add('second')
    claims = []
    original = worker.process_once
    def observe(value, startup):
        result = original(value, startup)
        if len(value.journal.status()['tasks']) == 2:
            second_polled.set()
        return result
    monkeypatch.setattr(worker, 'process_once', observe)
    def claimed(point):
        if point == 'after_claim':
            claims.append(runtime.current.coordinator.claimed['session_id'])
    case.fault = claimed
    second = start(runtime, 'second', room='456', raw=False)
    # Healthy exited capture entries may already have been reaped by the worker.
    wait_for(lambda: runtime.journal.session(second['session_id'])['phase'] == 'queued')
    assert second_polled.wait(10)
    assert all(t['state'] == 'queued' for t in runtime.journal.status()['tasks'])
    assert not claims and not runtime.authority._attempts
    release.set()
    wait_for(lambda: not runtime.journal.status()['units'])
    assert claims == [first['session_id'], second['session_id']]
    assert runtime.journal.session(second['session_id'])['intent']['raw_copy'] is False
    assert runtime.paused is None


def test_targeted_stop_and_shutdown_at_confirmed_h_leave_fifo_for_restart(runtime_case):
    case = runtime_case
    ready, source_release = case.hold('held-h')
    confirmed, release = Event(), Event()
    case.releases.append(release)
    runtime = case.build(shutdown_grace=0).start_runtime()
    accepted = start(runtime, 'held-h')
    assert ready.wait(10)
    bridge = runtime.captures[accepted['session_id']]['bridge']
    def fault(point):
        if point == 'confirmed_h':
            confirmed.set()
            assert release.wait(45)
    bridge._fault = fault
    source_release.set()
    assert confirmed.wait(30)
    assert runtime.stop(accepted['session_id'])['stop_result'] == 'capture_already_closed'
    assert not bridge.stop_event.is_set()
    receipt = runtime.journal.operation(bridge.handoff_operation)
    result = runtime.shutdown()
    assert not result['complete'] and not result['captures_joined']
    assert not result['authority_released'] and not runtime.authority._attempts
    release.set()
    wait_for(lambda: runtime.captures[accepted['session_id']]['done'])
    runtime.captures[accepted['session_id']]['thread'].join(5)
    assert runtime.shutdown()['complete']
    assert runtime.journal.session(accepted['session_id'])['phase'] == 'queued'
    assert len(runtime.journal.status()['units']) == 1
    restarted = case.build().start_runtime()
    wait_for(lambda: restarted.session_status(accepted['session_id'])['output_completed'])
    assert restarted.journal.operation(bridge.handoff_operation) == receipt
    assert not restarted.journal.status()['units']


def test_actual_post_h_exclusive_marker_close_fault_never_claims(runtime_case, monkeypatch):
    import ctypes
    from ctypes import wintypes
    from tikrec.capture_handoff_native import NativeHandle
    from tikrec.capture_handoff_marker import MARKER_NAME
    from tests.test_release_recovery_windows_close import protection
    case = runtime_case
    ready, source_release = case.hold('uncertain-h')
    runtime = case.build(shutdown_grace=0).start_runtime()
    accepted = start(runtime, 'uncertain-h')
    assert ready.wait(10)
    bridge = runtime.captures[accepted['session_id']]['bridge']
    protected = []
    original = NativeHandle.close
    def close(held):
        if held.path.name == MARKER_NAME and not protected:
            protection(held.handle, True)
            protected.append((held, held.handle))
        return original(held)
    monkeypatch.setattr(NativeHandle, 'close', close)
    source_release.set()
    try:
        wait_for(lambda: runtime.paused == 'capture_handoff_inputs_needs_attention')
        assert protected and not bridge.handoff_inputs_retired
        assert protected[0][0] in bridge.handoff_input_owners
        assert runtime.captures[accepted['session_id']]['result'].post_h_errors
        assert runtime.journal.session(accepted['session_id'])['phase'] == 'queued'
        assert not runtime.authority._attempts and runtime.current is None
        assert len(runtime.journal.status()['units']) == 1
        assert not runtime.shutdown()['complete']
    finally:
        for held, native in protected:
            # PROTECT_FROM_CLOSE proves the exact original never became reusable.
            protection(native, False)
            api = ctypes.WinDLL('kernel32', use_last_error=True)
            api.CloseHandle.argtypes, api.CloseHandle.restype = (wintypes.HANDLE,), wintypes.BOOL
            assert api.CloseHandle(native)
            held.fd, held.handle = None, None
