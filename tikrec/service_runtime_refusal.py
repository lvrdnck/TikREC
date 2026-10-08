"""Shutdown-only local retirement of the original guarded pre-writer refusal."""

import os
from dataclasses import asdict
from pathlib import Path

from .capture_handoff_marker import MARKER_NAME
from .session_journal_types import digest, require


def retire_refusal(runtime, sid, entry):
    """Prove the unchanged committed pre-H owner before closing its exact local lease.

    This never changes journal accounting, evidence, or capture_uncertain. Callers
    must have joined captures/finalizer and retired borrowed operations first.
    """
    authority, bridge = runtime.authority, entry['bridge']
    fence, lease = bridge.fence, bridge.lease
    if (not authority.cleanup_guards or bridge.failure is None or entry.get('result') is not None
            or fence.inputs is None or not entry['done'] or entry['thread'] is None):
        return False
    with runtime.lock, authority.lock:
        require(runtime.closed and runtime.stopping.is_set(), 'shutdown fencing required')
        require(not entry['thread'].is_alive() and entry['thread'].ident is not None,
                'original capture join unconfirmed')
        require(runtime.captures.get(sid) is entry and authority.bridges.get(sid) is bridge
                and bridge.authority is authority and bridge.lease in authority.leases
                and bridge.intent.session_id == sid and bridge.started,
                'original refusal owner identity changed')
        require(not fence.active and fence.inflight == 0 and not fence.cleanup_errors
                and fence.writer_openings == 0 and fence.sources_opened == fence.sources_closed
                and fence.sources_opened > 0, 'source/writer cleanup unconfirmed')
        require(fence.session_id == sid and fence.generation == bridge.binding['generation'],
                'original refusal generation changed')
        authority.assert_held()
        row, status = runtime.journal.session(sid), runtime.journal.status()
        require(row is not None and row['generation'] == fence.generation
                and row['phase'] == 'closing' and row['room'] is not None
                and digest(row['intent']) == digest(asdict(bridge.intent))
                and row['seal'] is None and row['task'] is None
                and any(b['session'] == sid and b['generation'] == fence.generation
                        and b['slot'] == bridge.binding['slot'] for b in status['bindings'])
                and any(u['session'] == sid for u in status['units'])
                and not any(t['session'] == sid for t in status['tasks']),
                'committed pre-H refusal ownership unconfirmed')
        require(sid not in authority.pending and not bridge.handoff_inputs_retired
                and not bridge.handoff_input_owners
                and runtime.journal.operation(bridge.handoff_operation) is None
                and not os.path.lexists(Path(bridge.intent.parts_path) / MARKER_NAME)
                and not os.path.lexists(bridge.intent.output_path), 'H/output ownership is ambiguous')
        # A closed fence cannot be reopened by an escaped callback; admission is also sealed.
        bridge.stop_event.set()
        if not fence.inputs.retire():
            return False
        guard = getattr(lease.handle, 'guard', None)
        require(guard is not None, 'original capture lease lacks native close proof')
        if not lease.closed:
            lease.assert_held()
            lease.close()
        # LifecycleLease.closed is set before close; retry only the retained original reference.
        guard.close_retired_reference()
        if guard.retained:
            lease.handle.close()
        require(lease.closed and lease.handle.closed and not guard.retained,
                'original refusal lease cleanup unconfirmed')
        entry['refusal_retired'] = {'session': sid, 'generation': fence.generation,
                                    'revision': row['revision']}
        return True


def retire_refusals(runtime, entries):
    """Keep each failed owner and every primary/secondary diagnostic reachable on retry."""
    confirmed = set()
    for sid, entry in entries:
        try:
            if retire_refusal(runtime, sid, entry):
                confirmed.add(sid)
        except BaseException as error:
            runtime.record_error(error)
        inputs = entry['bridge'].fence.inputs
        if inputs is not None:
            for error in inputs.errors:
                if not any(error is previous for previous in runtime.errors):
                    runtime.record_error(error)
    return confirmed


def sealed_refusals(runtime):
    """Retain the already-proved local closure after SQLite admission irreversibly sealed.

    No new journal reads are allowed here. The original committed proof preceded
    sealing, and every potential writer/borrower must remain retired.
    """
    confirmed = set()
    for sid, entry in runtime.captures.items():
        bridge, proof = entry['bridge'], entry.get('refusal_retired')
        fence, lease = bridge.fence, bridge.lease
        guard = getattr(lease.handle, 'guard', None)
        if (proof is not None and proof['session'] == sid
                and proof['generation'] == bridge.binding['generation'] == fence.generation
                and runtime.authority.bridges.get(sid) is bridge
                and bridge.authority is runtime.authority and lease in runtime.authority.leases
                and entry['done'] and not entry['thread'].is_alive()
                and not fence.active and not fence.inflight and not fence.cleanup_errors
                and not fence.writer_openings and fence.sources_opened == fence.sources_closed
                and fence.inputs.retired() and lease.closed and lease.handle.closed
                and guard is not None and not guard.retained):
            confirmed.add(sid)
    return confirmed


def retry_refusal_authority(runtime):
    """Retry guarded original catalog owners only after proved refusal closure and sealing."""
    for lease in (runtime.authority.owner, *runtime.authority.leases):
        guard = getattr(lease.handle, 'guard', None)
        if lease.closed and guard is not None:
            guard.close_retired_reference()
            if guard.retained:
                lease.handle.close()
    for held in (runtime.authority.state, runtime.authority.catalog, runtime.authority.media):
        held.close()
