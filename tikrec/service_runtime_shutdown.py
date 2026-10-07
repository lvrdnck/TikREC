"""Owned shutdown never drains the queue or equates uncertainty with safe exit."""

import time

from .service_runtime_worker import reap_captures, owned, capture_uncertain
from .session_journal_types import require


def authority_retired(runtime):
    """An emptied ExitStack alone does not prove that its failed closes retired."""
    authority = runtime.authority
    for lease in (authority.owner, *authority.leases):
        guard = getattr(lease.handle, 'guard', None)
        if not lease.closed or not lease.handle.closed or lease.cleanup_errors or guard is not None and guard.retained:
            return False
    return all(h.handle is None and h.fd is None for h in (authority.state, authority.catalog, authority.media))



def join_thread(runtime, thread, timeout):
    """Require an actual join; an interrupted, unstarted object is still uncertain."""
    try:
        thread.join(timeout)
        return not thread.is_alive()
    except BaseException as error:
        runtime.record_error(error)
        return False


def shutdown(runtime):
    """Stop starts/captures, give current finalizer grace, then exact-owner cleanup."""
    with runtime.lock:
        if runtime.authority_closed:
            return runtime.shutdown_result
        runtime.closed = True
        runtime.stopping.set()
        entries = tuple(runtime.captures.values())
    # Automation can be holding its own lock while a start is waiting for ours.
    if runtime.automation is not None:
        runtime.automation.stop()
    runtime.connections.cleanup(runtime)
    for entry in entries:
        if not entry['done']:
            try:
                bridge = entry['bridge']
                with runtime.authority.lock:
                    if any(b['session'] == bridge.intent.session_id
                           and b['generation'] == bridge.binding['generation']
                           for b in runtime.journal.status()['bindings']):
                        bridge.stop()
            except BaseException as error:
                runtime.record_error(error)
    deadline = time.monotonic() + runtime.grace
    captures_joined = True
    for entry in entries:
        thread = entry['thread']
        if thread is not None:
            captures_joined = join_thread(runtime, thread, max(0, deadline - time.monotonic())) and captures_joined
    runtime.wake.set()
    worker = runtime.worker
    worker_joined = worker is None
    if worker is not None:
        worker_joined = join_thread(runtime, worker, max(0, deadline - time.monotonic()))
        if not worker_joined:
            address, adapter = runtime.recovery_address, runtime.current
            try:
                if address is not None:
                    runtime.authority.cancel_release_recovery(*address)
                if adapter is not None:
                    # Accepted exact-owner cancel fences launch and owns child termination.
                    adapter.cancel(5)
            except BaseException as error:
                runtime.record_error(error)
            runtime.cleanup_requested.set()
            runtime.wake.set()
            worker_joined = join_thread(runtime, worker, 5)
    catalog_uncertain = runtime.connections.failed(runtime)
    if not catalog_uncertain and not runtime.connections.closing:
        try:
            reap_captures(runtime)
        except BaseException as error:
            runtime.record_error(error)
            catalog_uncertain = True
    alive = not captures_joined
    worker_alive = not worker_joined
    uncertain_capture = any(capture_uncertain(e) for e in runtime.captures.values())
    incomplete = alive or worker_alive or owned(runtime) or uncertain_capture or catalog_uncertain
    if not incomplete:
        try:
            runtime.connections.seal()
            runtime.authority.close()
            require(authority_retired(runtime), 'catalog/native authority cleanup remains unconfirmed')
            runtime.connections.restore()
            runtime.authority_closed = True
        except BaseException as error:
            runtime.record_error(error)
            incomplete = True
    runtime.shutdown_result = {'complete': not incomplete, 'captures_joined': not alive,
        'finalizer_joined': not worker_alive, 'authority_released': runtime.authority_closed,
        'reason': 'ownership_or_cleanup_unconfirmed' if incomplete else None,
        'diagnostic_count': len(runtime.errors), 'diagnostics_dropped': runtime.errors_dropped}
    return runtime.shutdown_result
