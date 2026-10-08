"""One tracked FIFO worker; durable work, not notifications, drives processing."""

from .journal_settlement import JournalSettlement
from .service_runtime_retirement import (retired, runner_retired, retained_runners,
    protect_lease, retire_guard_references, prune_terminal_runners)


def capture_uncertain(entry):
    """Keep unknown native teardown distinct from a lost notification."""
    bridge, result = entry['bridge'], entry.get('result')
    guard = getattr(bridge.lease.handle, 'guard', None)
    errors = getattr(result, 'post_h_errors', ())
    notification = getattr(result, 'notification_error', None)
    return (bridge.fence.active or bridge.fence.cleanup_errors or bridge.lease.cleanup_errors
        or not bridge.lease.closed or not bridge.lease.handle.closed
        or guard is not None and guard.retained
        or any(e is not notification or getattr(e, 'capture_cleanup_errors', ()) for e in errors))


def capture_cleanup_blocked(runtime, status):
    """Bound retained post-H owners even when their task already returned its unit."""
    bindings = {b['session'] for b in status['bindings']}
    return any(sid not in bindings and e['done'] and capture_uncertain(e)
               for sid, e in runtime.captures.items())


def prune_leases(runtime):
    """Discard only known-closed leases that never acquired a surviving bridge."""
    referenced = {id(b.lease) for b in runtime.authority.bridges.values()}
    runtime.authority.leases[:] = [lease for lease in runtime.authority.leases
        if id(lease) in referenced or not lease.closed or not lease.handle.closed
        or lease.cleanup_errors or getattr(getattr(lease.handle, 'guard', None), 'retained', False)]


def reap_captures(runtime):
    """Retire exited local capture owners only after known native/lease closure."""
    with runtime.lock:
        bindings = {b['session'] for b in runtime.journal.status()['bindings']}
        for sid, entry in tuple(runtime.captures.items()):
            thread, bridge = entry['thread'], entry['bridge']
            if not entry['done'] or thread is not None and thread.is_alive() or sid in bindings:
                continue
            if capture_uncertain(entry):
                continue
            runtime.captures.pop(sid)
            runtime.capture_errors.pop(sid, None)
            runtime.authority.bridges.pop(sid, None)
            if bridge.lease in runtime.authority.leases:
                runtime.authority.leases.remove(bridge.lease)
        prune_leases(runtime)
        if runtime.resource_policy is not None:
            # Completed native references are not lifetime history. Unknown originals stay.
            runtime.authority.native_close_guards[:] = [g for g in runtime.authority.native_close_guards
                                                       if g.retained]


def cleanup_current(runtime):
    """Request accepted local cleanup on the worker's original SQLite thread."""
    adapter = runtime.current
    runners = tuple(runtime.authority._attempts.values())
    for runner in runners:
        cap = getattr(runner, 'settlement_owner', None)
        if cap is not None and cap.operation is not None:
            for reader in cap.readers:
                if reader.connection is not None:
                    for _, error in reader.cleanup():
                        runner._error(error)
                        runtime.record_error(error)
        elif adapter is not None and adapter.coordinator is runner and not runner_retired(runner):
            try:
                adapter.close(5)
            except BaseException as error:
                runtime.record_error(error)
        # Earlier failed work outside current is pinned, not adopted or replayed.
        retire_guard_references(runtime, runner)
        if runner_retired(runner):
            runner.closed = True
    if runtime.current is not None and retired(runtime.current):
        runtime.current = None
    prune_terminal_runners(runtime)
    for owner in tuple(runtime.authority._recovery_owners.values()):
        try:
            owner.close()
        except BaseException as error:
            runtime.record_error(error)
    runtime.connections.cleanup(runtime)


def owned(runtime):
    """Refuse worker retirement while thread-affine or native owners remain."""
    return (runtime.current is not None and not retired(runtime.current)
            or bool(retained_runners(runtime))
            or any(o.has_retained_ownership() for o in runtime.authority._recovery_owners.values())
            or runtime.connections.has_ownership())


def process_once(runtime, startup):
    """Recover eligible prepared success or run one real oldest queued recording."""
    status = runtime.journal.status()
    running = next((t for t in status['tasks'] if t['state'] == 'running'), None)
    if running is not None:
        if not startup:
            runtime.paused = 'unfinished_attempt_needs_attention'
            return
        record = runtime.journal.settlement(running['token'])
        if record is None or record['preparation'] is None:
            runtime.paused = 'unsupported_unfinished_phase'
            return
        reason = runtime.storage_reason('finalization')
        if reason:
            runtime.paused = reason
            return
        with runtime.lock:
            if runtime.stopping.is_set():
                return
            runtime.recovery_address = (running['session'], running['token'])
        def recovery_fault(point):
            # If expiry preceded capability creation, the initial cancel was only a hint.
            if runtime.cleanup_requested.is_set():
                runtime.authority.cancel_release_recovery(*runtime.recovery_address)
            runtime.recovery_fault(point)
        try:
            runtime.authority.recover_prepared_release(*runtime.recovery_address,
                                                       fault=recovery_fault)
        finally:
            runtime.recovery_address = None
        return True
    if any(t['state'] in {'failed', 'blocked'} for t in status['tasks']):
        runtime.paused = 'unsupported_unfinished_phase'
        return
    oldest = next((t for t in status['tasks'] if t['state'] == 'queued'), None)
    if oldest is None:
        return False
    reason = runtime.storage_reason('finalization')
    if reason:
        runtime.paused = reason
        return
    with runtime.lock:
        if runtime.stopping.is_set():
            return
        entry = runtime.captures.get(oldest['session'])
        if entry is not None:
            # Confirmed H frees the slot before exclusive local proof handles unwind.
            # Do not spend its single-use attempt, or leapfrog the oldest FIFO task.
            if not entry['done'] or entry['thread'] is not None and entry['thread'].is_alive():
                return False
            if not entry['bridge'].handoff_inputs_retired:
                runtime.paused = 'capture_handoff_inputs_needs_attention'
                return False
        options = dict(runtime.settlement_options)
        fault = options.pop('fault', lambda _: None)
        def runtime_fault(point):
            if point == 'after_owned_inputs':
                protect_lease(adapter.coordinator)
            fault(point)
            if runtime.resource_policy is not None and point in {
                    'before_assembly_writer', 'before_validation_authority', 'before_publication_preparation',
                    'before_publication_fence'}:
                from .session_journal_types import require
                require(runtime.storage_reason('finalization') is None,
                        'operational finalization storage pressure; preserve unfinished work')
            if point in {'before_release_preparation', 'before_terminal_release'}:
                # Unrelated borrowed SQLite cleanup is still local outstanding ownership.
                from .session_journal_types import require
                require(not runtime.connections.failed(runtime), 'runtime catalog cleanup remains unconfirmed')
        adapter = JournalSettlement(runtime.authority, ffmpeg=runtime.ffmpeg,
            ffprobe=runtime.ffprobe, fault=runtime_fault, **options)
        adapter.coordinator.native_close_guards = []
        runtime.current = adapter
    try:
        adapter.run()
    finally:
        if runtime.resource_policy is not None and getattr(adapter.coordinator, 'candidate_budget_refused', False):
            # Preserve this category even when original native cleanup already retired.
            runtime.paused = 'candidate_budget_needs_attention'
        if retired(adapter):
            # A failed capability stays visible to original-owner retirement checks.
            # Its outstanding unit bounds this registry; success history isn't cached.
            if adapter.error is None:
                runtime.authority._attempts.pop(adapter.coordinator.token, None)
            runtime.current = None
        prune_terminal_runners(runtime)
    return True


def processing_loop(runtime):
    """Reconcile missed H hints; pause once on uncertainty rather than retrying it."""
    startup = True
    while True:
        runtime.wake.clear()
        try:
            if not runtime.connections.failed(runtime):
                reap_captures(runtime)
            if runtime.stopping.is_set():
                if runtime.cleanup_requested.is_set():
                    runtime.cleanup_requested.clear()
                    cleanup_current(runtime)
                if not owned(runtime):
                    return
            elif runtime.connections.failed(runtime):
                runtime.paused = runtime.paused or 'catalog_cleanup_needs_attention'
            elif runtime.paused in {None, 'low_free_space', 'storage_unavailable'}:
                runtime.paused = None
                progressed = process_once(runtime, startup)
                if runtime.paused not in {'low_free_space', 'storage_unavailable'}:
                    startup = False
                # A successful task immediately advances FIFO, without another H hint.
                if progressed and runtime.paused is None and runtime.journal.status()['tasks']:
                    continue
        except BaseException as error:
            runtime.record_error(error)
            if runtime.paused != 'candidate_budget_needs_attention':
                runtime.paused = 'finalizer_needs_attention'
            startup = False
        runtime.wake.wait(runtime.poll_interval)
