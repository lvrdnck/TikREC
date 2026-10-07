"""Exact native finalizer retirement; historic error flags are not live ownership."""

import os

from .release_recovery_handles import NativeCloseGuard


def protect_lease(runner):
    """Protect the newly acquired finalizer lease before any success cleanup."""
    if os.name != 'nt':
        return
    import msvcrt
    lease = runner.guard.lifecycle
    if getattr(lease.handle, 'guard', None) is None:
        raw = lease.handle
        descriptor = raw.fileno()
        guard = NativeCloseGuard(runner, msvcrt.get_osfhandle(descriptor), descriptor)
        lease.handle = guard.stream(raw)


def lease_retired(lease):
    """Use current exact native proof; unguarded cleanup errors remain uncertain."""
    guard = getattr(lease.handle, 'guard', None)
    return (lease.closed and lease.handle.closed
            and (not guard.retained if guard is not None else not lease.cleanup_errors))


def runner_retired(runner):
    """Include resources belonging to failed coordinators outside runtime.current."""
    if any(g.retained for g in getattr(runner, 'native_close_guards', ())):
        return False
    cap = getattr(runner, 'settlement_owner', None)
    if cap is not None and cap.operation is not None:
        for key, held in cap.objects:
            if key == 'lease':
                if not lease_retired(held):
                    return False
            elif held.handle is not None or getattr(held, 'fd', None) is not None:
                return False
        return (all(r.connection is None for r in cap.readers)
                and all(c['process'].closed for c in runner.children))
    guard = runner.guard
    if guard is not None:
        if (any(h.handle is not None for h in guard.handles)
                or guard.extra_handles or guard.extra_descriptors
                or guard.lifecycle is not None and not lease_retired(guard.lifecycle)):
            return False
    if runner.scratch is not None:
        evidence = runner.scratch.protection_evidence()
        if evidence['workspace_retained'] or evidence['artifacts_retained']:
            return False
    manifest = getattr(runner, 'manifest_owner', None)
    if manifest is not None and manifest.fence_owner is not None:
        if manifest.fence_owner.connection is not None:
            return False
    return all(c['process'].closed and c['process'].evidence().state in
               {'not_created', 'confirmed_exited'} for c in runner.children)


def retired(adapter):
    """Inspect native lifetime independently of durable completion and diagnostics."""
    return runner_retired(adapter.coordinator)


def retained_runners(runtime):
    """Return a bounded snapshot of exact original coordinators still owning work."""
    return tuple(r for r in runtime.authority._attempts.values() if not runner_retired(r))


def retire_guard_references(runtime, runner):
    """Explicit cleanup touches only proven original objects, never reused numbers."""
    for guard in getattr(runner, 'native_close_guards', ()):
        if not guard.retained:
            continue
        try:
            # A closed original can retire its duplicate without touching a reused fd.
            guard.close_retired_reference()
            if guard.retained:
                guard.close()
        except BaseException as error:
            runner._error(error)
            runtime.record_error(error)


def prune_terminal_runners(runtime):
    """Keep outstanding failed owners, not already-retired completed error history."""
    for token, runner in tuple(runtime.authority._attempts.items()):
        if runner_retired(runner) and getattr(runner, 'settlement_owner', None) is not None:
            record = runtime.journal.settlement(token)
            if record is not None and record['state'] == 'released':
                runtime.authority._attempts.pop(token, None)
