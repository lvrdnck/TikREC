"""Bounded internal projections; capture availability is never output completion."""

from .recording_manager import RecordingAmbiguous, RecordingNotFound
from .session_journal_types import identifier
from .service_runtime_worker import capture_cleanup_blocked


def session_status(runtime, sid):
    """Read immutable origin identity and independent current phase by UUID."""
    identifier(sid)
    with runtime.lock:
        row = runtime.journal.session(sid)
        if row is None:
            raise RecordingNotFound('recording session not found')
        intent, task = row['intent'], row['task']
        entry = runtime.captures.get(sid, {})
        bound = any(b['session'] == sid for b in runtime.journal.status()['bindings'])
        state = (entry.get('state', 'needs_attention') if bound else
                 'completed' if row['phase'] in {'completed', 'no_assembly'} else 'finalizing')
        return {'session_id': sid, 'state': state, 'active': bound,
            'source_url': 'https://www.tiktok.com/@' + row['creator'] + '/live',
            'creator': row['creator'], 'room_id': row['room'],
            'output_path': intent['output_path'], 'parts_directory': intent['parts_path'],
            'raw_copy_enabled': intent['raw_copy'], 'started_at': intent['started_at'],
            'stop_requested': bool(row['stop']), 'generation': row['generation'],
            'origin_slot_id': 'slot-' + str(row['origin_slot']),
            'capture_state': row['phase'] if bound else 'closed',
            'finalization_state': None if task is None else task['state'],
            'final_output_path': intent['output_path'] if row['phase'] == 'completed' else None,
            'output_completed': row['phase'] == 'completed',
            'bytes_written': entry.get('bytes_written', 0),
            'interrupted': bool(row['stop']),
            'needs_attention': (bound and (not entry or entry.get('done', False))
                or task is not None and task['state'] != 'completed'
                and runtime.paused not in {None, 'low_free_space', 'storage_unavailable'}),
            'error': 'capture_needs_attention' if sid in runtime.capture_errors else None}


def unknown_health(runtime):
    """Unknown catalog facts are unavailable, never invented zero counts."""
    return {'capacity': 2, 'available_slots': 0, 'available': False,
        'active_count': None, 'shutting_down': runtime.closed,
        'admission_reason': 'catalog_cleanup_needs_attention',
        'finalization': {'outstanding_units': None, 'limit': 8, 'tasks': None,
            'running': runtime.current is not None or runtime.recovery_address is not None,
            'paused_reason': runtime.paused or 'catalog_needs_attention',
            'errors': len(runtime.errors), 'errors_dropped': runtime.errors_dropped},
        'shutdown': runtime.shutdown_result}


def health(runtime):
    """Report the two capture slots and separate worker/backlog/storage barriers."""
    reason = runtime.storage_reason()
    with runtime.lock:
        if runtime.connections.failed(runtime):
            return unknown_health(runtime)
        try:
            status = runtime.journal.status()
        except Exception as error:
            runtime.record_error(error)
            return unknown_health(runtime)
        available = sum(b['session'] is None for b in status['bindings'])
        if len(status['units']) >= 8:
            reason = 'finalization_backlog_full'
        if runtime.authority.pending:
            reason = 'handoff_unreconciled'
        if capture_cleanup_blocked(runtime, status):
            reason = 'capture_cleanup_needs_attention'
        if runtime.closed or not runtime.started or reason:
            available = 0
        return {'capacity': 2, 'available_slots': available, 'available': available > 0,
            'active_count': sum(b['session'] is not None for b in status['bindings']),
            'shutting_down': runtime.closed, 'admission_reason': reason,
            'finalization': {'outstanding_units': len(status['units']), 'limit': 8,
                'tasks': len(status['tasks']), 'running': runtime.current is not None or runtime.recovery_address is not None,
                'paused_reason': runtime.paused, 'errors': len(runtime.errors),
                'errors_dropped': runtime.errors_dropped},
            'shutdown': runtime.shutdown_result}


def recordings(runtime):
    """Keep capture slots separate from at-most-eight outstanding artifact sessions."""
    with runtime.lock:
        status = runtime.journal.status()
        slots = []
        for binding in status['bindings']:
            sid = binding['session'] or runtime.latest.get(binding['slot'])
            value = {'state': 'idle', 'active': False} if sid is None else session_status(runtime, sid)
            slots.append({**value, 'slot_id': 'slot-' + str(binding['slot'])})
        return {**health(runtime), 'slots': slots,
            'finalization_sessions': [session_status(runtime, t['session']) for t in status['tasks']]}


def singular(runtime):
    """Refuse ambiguity rather than hiding an old outstanding artifact owner."""
    with runtime.lock:
        units = runtime.journal.status()['units']
        if len(units) > 1:
            raise RecordingAmbiguous('multiple recordings require a session ID')
        if units:
            return session_status(runtime, units[0]['session'])
        sid = next(reversed(runtime.latest.values()), None)
        return {'state': 'idle', 'active': False} if sid is None else session_status(runtime, sid)


def stop(runtime, sid):
    """Target capture UUID only; finalization-only stop cannot cancel a worker."""
    with runtime.lock:
        if sid is None:
            value = singular(runtime)
            sid = value.get('session_id')
            if sid is None:
                return value
        value = session_status(runtime, sid)
        if value['output_completed'] or value['state'] == 'completed':
            raise RecordingNotFound('active recording session not found')
        if not value['active']:
            return {**value, 'stop_result': 'capture_already_closed'}
        entry = runtime.captures.get(sid)
        if entry is None or entry['done']:
            return {**value, 'stop_result': 'capture_needs_attention'}
        # H and stop use the same authority fence. A concurrent H may win first.
        with runtime.authority.lock:
            if not any(b['session'] == sid for b in runtime.journal.status()['bindings']):
                return {**session_status(runtime, sid), 'stop_result': 'capture_already_closed'}
            entry['bridge'].stop()
        return session_status(runtime, sid)
