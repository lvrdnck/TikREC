"""Frozen original resource scope and independent, explicit exact-object cleanup."""

import json
from dataclasses import asdict

from .session_journal_types import encode, require


def resources(runner):
    """Capture every attempt-owned object; shared root/catalog authority is excluded."""
    guard, scratch, manifest = runner.guard, runner.scratch, runner.manifest_owner
    require(not guard.extra_descriptors and guard.extra_handles == [manifest.stage],
            'unexplained retained input resources')
    native = [(f'input:{i}', held) for i, held in enumerate(guard.handles)]
    native += [('manifest:successor', manifest.stage), ('scratch:workspace', scratch.workspace)]
    native += [('scratch:' + name, held) for name, held in sorted(scratch.artifacts.items())]
    require(len({id(held) for _, held in native}) == len(native), 'aliased cleanup scope')
    scope = []
    for key, held in native:
        require(held.handle is not None, 'resource protection already closed')
        held.verify()
        scope.append({'key': key, 'kind': 'native', 'evidence': {'path': str(held.path),
            'identity': asdict(held.identity), 'size': held.size, 'stamp': held.stamp}})
    lease = guard.lifecycle
    lease.assert_held()
    require(not guard.cleanup_errors, 'prior input/lease cleanup failure prevents success')
    scope.append({'key': 'lease', 'kind': 'lease', 'evidence': {'mode': lease.mode, 'slot': lease.slot,
        'identity': lease.identity, 'root': str(lease.root)}})
    return tuple([*native, ('lease', lease)]), json.loads(encode(scope))


def children_complete(runner):
    """Require every original child's confirmed exit, final streams and exact cleanup."""
    for child in runner.children:
        evidence = child['process'].evidence()
        require(child['process'].closed and child['exit_recorded'] and child['diagnostics_recorded']
                and child['cleanup_recorded'] and evidence.state == 'confirmed_exited'
                and evidence.active_processes == 0 and child['streams'].record(evidence)['complete'],
                'retained or unknown child prevents settlement authority')
        native = child['process'].native
        require(native is not None and native.process is None and native.thread is None and native.job is None
                and not native.streams.child and not native.streams.readers, 'native child controls still retained')
    return True


def check_children(runner, facts):
    """Match each exact local child's final exit and complete diagnostic hash to its receipt."""
    from .session_journal_types import digest
    children_complete(runner)
    require(len(runner.children) == len(facts), 'local execution scope incomplete')
    for child, fact in zip(runner.children, facts, strict=True):
        evidence = child['process'].evidence()
        require(child['launch'] == fact['launch'] and asdict(evidence.identity) == fact['identity']
                and fact['exit'] == {'state': evidence.state, 'identity': asdict(evidence.identity),
                    'code': evidence.root_exit_code, 'active': evidence.active_processes}
                and digest(child['streams'].record(evidence)) == fact['diagnostics_hash'],
                'local child/diagnostic evidence conflicts')


def cleanup(cap):
    """Try each captured exact object once; failed close never blocks another safe close."""
    runner, errors, results = cap.runner, [], []
    for key, held in cap.objects:
        confirmed = False
        prior_errors = len(held.cleanup_errors) if key == 'lease' else 0
        try:
            held.close()
            confirmed = (held.closed and held.handle.closed if key == 'lease' else
                         held.handle is None and getattr(held, 'fd', None) is None)
            require(confirmed, 'native cleanup did not confirm release: ' + key)
        except BaseException as error:
            errors.append(error)
            runner._error(error)
            if key == 'lease':
                for secondary in held.cleanup_errors[prior_errors:]:
                    if secondary is not error:
                        errors.append(secondary)
                        runner._error(secondary)
        results.append({'key': key, 'closed': confirmed})
        # Test barrier runs after the result exists, outside every SQLite/gate lock.
        try:
            runner._fault('after_release_resource_' + key.replace(':', '_'))
        except BaseException as error:
            errors.append(error)
            runner._error(error)
    for key, held in cap.objects:
        if key == 'manifest:successor' and held.handle is None and held.fd is None:
            if held in runner.guard.extra_handles:
                runner.guard.extra_handles.remove(held)
    runner.guard.acquired = False
    runner.guard.closed = not runner.guard.retained
    readers_complete = True
    for reader in cap.readers:
        new = reader.cleanup() if reader.connection is not None else ()
        for _, error in new:
            runner._error(error)
        errors.extend(error for _, error in reader.errors)
        readers_complete = readers_complete and reader.connection is None
    manifest_reader = runner.manifest_owner.fence_owner
    if manifest_reader is not None:
        # This can only be an already-closed, failure-free reader from fresh proof.
        readers_complete = readers_complete and manifest_reader.connection is None
    diagnostic_count = len(errors)
    evidence = {'preparation_operation': cap.operation, 'binding_hash': cap.binding_hash,
        'resources': results, 'readers_complete': readers_complete, 'children_complete': True,
        'cleanup_complete': all(r['closed'] for r in results) and readers_complete and not errors,
        'diagnostics': [repr(e)[:2048] for e in errors[:32]], 'diagnostics_dropped': max(0, diagnostic_count - 32)}
    cap.cleanup_result, cap.first_cleanup_error = evidence, errors[0] if errors else None
    runner.closed = evidence['cleanup_complete']
    return evidence
