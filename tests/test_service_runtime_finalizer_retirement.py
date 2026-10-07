"""Actual Windows finalizer close failure cannot be treated as safe retirement."""

import ctypes
import os
from ctypes import wintypes
from threading import Event

import pytest

pytestmark = pytest.mark.skipif(os.name != 'nt', reason='native Windows runtime')

from tests.service_runtime_helpers import runtime_case, managed_process, start, wait_for, hashes
from tests.test_release_recovery_windows_close import protection


@pytest.mark.parametrize('outside_current', [False, True])
def test_protected_finalizer_lease_retains_authority_and_unit(runtime_case, outside_current):
    import msvcrt
    case = runtime_case
    prepared = Event()
    runtime = case.build(shutdown_grace=0).start_runtime()
    held = {}
    api = ctypes.WinDLL('kernel32', use_last_error=True)
    api.CloseHandle.argtypes, api.CloseHandle.restype = (wintypes.HANDLE,), wintypes.BOOL
    api.GetHandleInformation.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
    api.GetHandleInformation.restype = wintypes.BOOL
    def fault(point):
        if point == 'after_release_preparation':
            adapter = runtime.current
            lease = adapter.coordinator.guard.lifecycle
            native = msvcrt.get_osfhandle(lease.handle.fileno())
            protection(native, True)
            held.update(adapter=adapter, lease=lease, native=native)
            case.adapters.append(adapter)
            prepared.set()
    case.fault = fault
    accepted = start(runtime, 'protected-finalizer')
    try:
        assert prepared.wait(30)
        wait_for(lambda: runtime.paused == 'finalizer_needs_attention')
        lease, adapter = held['lease'], held['adapter']
        assert lease.closed and lease.handle.closed and lease.cleanup_errors
        flags = wintypes.DWORD()
        assert api.GetHandleInformation(held['native'], ctypes.byref(flags)) and flags.value & 2
        record = runtime.journal.settlement(adapter.coordinator.token)
        assert record['state'] == 'cleanup_incomplete'
        assert adapter.error is lease.cleanup_errors[0]
        assert len(runtime.journal.status()['units']) == 1
        before = hashes(runtime.root)
        original = runtime.journal.session(accepted['session_id'])
        h_operation = record['preparation']['binding']['h_operation']
        handoff = runtime.journal.operation(h_operation)
        if outside_current:
            # A failed coordinator's ownership survives loss of the current projection.
            with runtime.lock:
                runtime.current = None
        result = runtime.shutdown()
        # Baseline 90156913 reports complete and releases the catalog here.
        assert not result['complete'] and not result['authority_released'], result
        assert adapter.coordinator.token in runtime.authority._attempts
        assert len(runtime.journal.status()['units']) == 1
        assert not runtime.session_status(accepted['session_id'])['output_completed']
        assert not runtime.shutdown()['complete']
        assert runtime.journal.settlement(adapter.coordinator.token) == record
        assert adapter.error is lease.cleanup_errors[0]
        assert len(adapter.coordinator.errors) <= 32 and len(runtime.errors) <= 32
    finally:
        if held:
            # Close protection proves this exact fixture handle never became reused.
            protection(held['native'], False)
            assert api.CloseHandle(held['native'])
    # Confirmation retires only native ownership; the failed receipt is historical.
    assert runtime.shutdown()['complete']
    assert runtime.journal.settlement(adapter.coordinator.token) == record
    assert len(runtime.journal.status()['units']) == 1
    case.fault = lambda _: None
    restarted = case.build().start_runtime()
    wait_for(lambda: restarted.session_status(accepted['session_id'])['output_completed'])
    assert hashes(restarted.root) == before
    current = restarted.journal.session(accepted['session_id'])
    assert all(current[k] == original[k] for k in ('intent', 'seal', 'seal_hash', 'generation', 'origin_slot'))
    assert restarted.journal.operation(h_operation) == handoff
    assert restarted.journal.settlement(adapter.coordinator.token)['cleanup'] == record['cleanup']
    next_item = start(restarted, 'next-success', room='456')
    wait_for(lambda: restarted.session_status(next_item['session_id'])['output_completed'])
    assert not restarted.journal.status()['units']
    assert restarted.journal._read(lambda db: db.execute('SELECT count(*) FROM release_results').fetchone()[0]) == 1
    assert restarted.journal._read(lambda db: db.execute('SELECT count(*) FROM release_recovery_results').fetchone()[0]) == 1


def test_reported_lease_error_after_actual_close_is_not_retained_native_work(runtime_case, monkeypatch):
    case = runtime_case
    first = OSError('lease reported after confirmed native close')
    held = []
    runtime = case.build().start_runtime()
    def fault(point):
        if point == 'after_release_preparation':
            adapter = runtime.current
            held.append(adapter)
            lease = adapter.coordinator.guard.lifecycle
            close = lease.close
            def reported():
                close()
                raise first
            monkeypatch.setattr(lease, 'close', reported)
    case.fault = fault
    accepted = start(runtime, 'close-then-error')
    wait_for(lambda: runtime.paused == 'finalizer_needs_attention')
    adapter = held[0]
    assert adapter.error is first
    assert all(not g.retained for g in adapter.coordinator.native_close_guards)
    assert runtime.current is None
    assert runtime.journal.settlement(adapter.coordinator.token)['state'] == 'cleanup_incomplete'
    assert len(runtime.journal.status()['units']) == 1
    assert runtime.shutdown()['complete']
    assert not runtime.session_status(accepted['session_id'])['output_completed']


@pytest.mark.parametrize('same_file', [False, True])
def test_explicit_cleanup_refuses_reused_descriptor_then_retires_only_duplicate(runtime_case, same_file):
    import msvcrt
    from tikrec.lifecycle_lock import LOCK_NAME
    case = runtime_case
    runtime = case.build(shutdown_grace=0).start_runtime()
    held, streams = {}, []
    api = ctypes.WinDLL('kernel32', use_last_error=True)
    api.CloseHandle.argtypes, api.CloseHandle.restype = (wintypes.HANDLE,), wintypes.BOOL
    def fault(point):
        if point == 'after_release_preparation':
            lease = runtime.current.coordinator.guard.lifecycle
            descriptor = lease.handle.fileno()
            native = msvcrt.get_osfhandle(descriptor)
            protection(native, True)
            held.update(adapter=runtime.current, native=native, descriptor=descriptor)
    case.fault = fault
    start(runtime, 'reuse')
    original_closed = False
    try:
        wait_for(lambda: runtime.paused == 'finalizer_needs_attention')
        target = runtime.root / (LOCK_NAME if same_file else 'fresh.bin')
        # CRT close already returned this number despite the protected kernel owner.
        for _ in range(64):
            stream = target.open('r+b' if same_file else 'w+b')
            streams.append(stream)
            if stream.fileno() == held['descriptor']:
                break
        assert streams[-1].fileno() == held['descriptor']
        fresh = streams[-1]
        fresh_native = msvcrt.get_osfhandle(fresh.fileno())
        assert fresh_native != held['native']
        for _ in range(2):
            assert not runtime.shutdown()['complete']
            assert not fresh.closed and msvcrt.get_osfhandle(fresh.fileno()) == fresh_native
            assert len(runtime.journal.status()['units']) == 1
        guard = held['adapter'].coordinator.native_close_guards[0]
        assert guard.retained and any('descriptor identity' in str(e) for e in runtime.errors)
        protection(held['native'], False)
        assert api.CloseHandle(held['native'])
        original_closed = True
        assert runtime.shutdown()['complete']
        assert not guard.retained and not fresh.closed
        assert msvcrt.get_osfhandle(fresh.fileno()) == fresh_native
        assert len(runtime.journal.status()['units']) == 1
    finally:
        if held and not original_closed:
            protection(held['native'], False)
            assert api.CloseHandle(held['native'])
        for stream in streams:
            stream.close()


def test_failed_terminal_reader_outside_current_is_cleaned_on_original_worker(runtime_case, monkeypatch):
    from threading import get_ident
    from tests.test_journal_settlement_cleanup import inject_transaction
    case = runtime_case
    runtime = case.build(shutdown_grace=0).start_runtime()
    first = OSError('terminal reader remains native SQLite ownership')
    retained = inject_transaction(runtime.journal, monkeypatch, 'settle_owned_success', close=first)
    accepted = start(runtime, 'terminal-reader')
    wait_for(lambda: runtime.paused == 'finalizer_needs_attention')
    adapter = runtime.current
    assert adapter is not None and retained
    assert adapter.capability.readers[-1].errors[0][1] is first
    token = adapter.coordinator.token
    record = runtime.journal.settlement(token)
    assert record['state'] == 'released'
    assert runtime.session_status(accepted['session_id'])['output_completed']
    assert not runtime.journal.status()['units']
    close, threads = retained[0].close, []
    def observed():
        threads.append(get_ident())
        return close()
    monkeypatch.setattr(retained[0], 'close', observed)
    with runtime.lock:
        runtime.current = None
    assert not runtime.shutdown()['complete']
    assert token in runtime.authority._attempts and runtime.worker.is_alive()
    assert all(reader.connection is not None for reader in adapter.capability.readers[-1:])
    retained[0].close_error = None
    assert runtime.shutdown()['complete']
    assert threads and set(threads) == {runtime.worker.ident}
    assert get_ident() not in threads
    assert runtime.authority._attempts == {}
    assert runtime.journal.settlement(token) == record
    assert not runtime.journal.status()['units']
