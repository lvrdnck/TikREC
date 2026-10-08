"""Deliberate bounded transport facts over the accepted isolated runtime."""

import math
from pathlib import Path

from . import __version__
from .creator_identity import validate_creator_handle
from .session_journal_types import identifier, require


CAPABILITY = 'durable_finalization_v1'
REASONS = frozenset({
    'finalization_backlog_full', 'low_free_space', 'storage_unavailable',
    'catalog_cleanup_needs_attention', 'catalog_needs_attention',
    'handoff_unreconciled', 'capture_cleanup_needs_attention',
    'capture_handoff_inputs_needs_attention', 'finalizer_needs_attention',
    'unsupported_unfinished_phase', 'worker_launch_failed', 'service_shutting_down',
    'capture_needs_attention', 'ownership_or_cleanup_unconfirmed',
    'request_cleanup_needs_attention', 'request_threads_unconfirmed',
    'monitor_cleanup_needs_attention', 'transport_needs_attention',
    'unfinished_attempt_needs_attention',
    'listener_cleanup_needs_attention',
})


def reason(value):
    """Expose fixed categories while keeping unknown internal messages private."""
    return value if value in REASONS else None if value is None else 'transport_needs_attention'


def number(value):
    """Unknown counters/times remain null rather than fabricated zero facts."""
    return value if type(value) in {int, float} and math.isfinite(value) and value >= 0 else None


def path(value):
    """Allow bounded local artifact paths, never URLs or multiline diagnostics."""
    if value is None:
        return None
    require(type(value) is str and len(value.encode('utf-8')) <= 1024
            and '://' not in value and not any(ord(c) < 32 for c in value),
            'artifact path is not transportable')
    return value


def shutdown_projection(value):
    """Project only owned shutdown facts, without serializing exceptions/owners."""
    if value is None:
        return None
    return {**{key: value.get(key) is True for key in
        ('complete', 'captures_joined', 'finalizer_joined', 'authority_released')},
        'reason': reason(value.get('reason')),
        'diagnostic_count': number(value.get('diagnostic_count')),
        'diagnostics_dropped': number(value.get('diagnostics_dropped'))}


def session_projection(runtime, value):
    """Preserve original identity and distinguish capture closure from output proof."""
    if 'session_id' not in value:
        return {'state': 'idle', 'active': False}
    sid = value['session_id']
    identifier(sid)
    creator = validate_creator_handle(value['creator'])
    completed = value.get('output_completed') is True
    if completed:
        # A generic phase or publication flag alone is insufficient transport proof.
        row = runtime.journal.session(sid)
        task = None if row is None else row['task']
        require(row is not None and row['phase'] == 'completed' and task is not None
                and task['state'] == 'completed' and task['token'] is not None,
                'completed output lacks an owned terminal task')
        settlement = runtime.journal.settlement(task['token'])
        require(settlement is not None and settlement['state'] == 'released'
                and settlement['preparation']['binding']['session_id'] == sid
                and value.get('output_path') == row['intent']['output_path'],
                'completed output lacks durable release proof')
    capture_state = value.get('capture_state')
    finalization_state = value.get('finalization_state')
    require(capture_state in {'reserved', 'capturing', 'closing', 'closed'})
    require(finalization_state in {None, 'queued', 'running', 'failed', 'blocked', 'completed'})
    state = value.get('state')
    require(state in {'resolving', 'recording', 'reconnecting', 'recovering_network',
        'recovery_wait', 'finalizing', 'completed', 'needs_attention', 'failed'})
    if capture_state == 'closed' and finalization_state is None and state == 'completed':
        finalization_state = 'no_assembly'
    with runtime.lock:
        entry = runtime.captures.get(sid)
        # Closed/restarted captures have no measured byte counter in the local map.
        written = None if entry is None else number(entry.get('bytes_written'))
    output = path(value.get('output_path'))
    result = {'session_id': sid, 'state': state, 'active': value.get('active') is True,
        'source_url': 'https://www.tiktok.com/@' + creator + '/live',
        'creator': creator, 'room_id': value.get('room_id'),
        'origin_slot_id': value['origin_slot_id'], 'generation': number(value.get('generation')),
        'output_path': output, 'parts_directory': path(value.get('parts_directory')),
        'raw_copy_enabled': value.get('raw_copy_enabled') is True,
        'started_at': number(value.get('started_at')), 'bytes_written': written,
        'stop_requested': value.get('stop_requested') is True,
        'interrupted': value.get('interrupted') is True,
        'capture_state': capture_state, 'finalization_state': finalization_state,
        'output_completed': completed, 'final_output_path': output if completed else None,
        'needs_attention': value.get('needs_attention') is True,
        'error': reason(value.get('error'))}
    require(result['origin_slot_id'] in {'slot-1', 'slot-2'})
    from .session_journal_types import room
    room(result['room_id'])
    if 'stop_result' in value:
        require(value['stop_result'] in {'capture_already_closed', 'capture_needs_attention'})
        result['stop_result'] = value['stop_result']
    return result


class RuntimeHTTPController:
    """Expose transport projections; the supplied runtime remains the sole authority."""

    def __init__(self, runtime):
        self.runtime = runtime

    def session_status(self, sid):
        """Lookup exact original UUID, including audited durable terminal history."""
        identifier(sid)
        return session_projection(self.runtime, self.runtime.session_status(sid))

    def status(self):
        """Keep singular ambiguity across all outstanding capture/artifact owners."""
        return session_projection(self.runtime, self.runtime.status())

    def start(self, url, output, *, raw_copy=False):
        """Delegate exactly once; lost transport acknowledgement never retries capture."""
        path(output)
        path(str(Path(output).with_suffix('.parts')))
        value = session_projection(self.runtime, self.runtime.start(url, output, raw_copy=raw_copy))
        return {**value, 'slot_id': value['origin_slot_id']}

    def stop(self, sid=None):
        """Delegate capture-only stop and preserve finalization-only no-op semantics."""
        return session_projection(self.runtime, self.runtime.stop(sid))

    def health(self):
        """Report physical free slots separately from backlog/storage admission refusal."""
        runtime = self.runtime
        value = runtime.health()
        active = number(value.get('active_count'))
        # The validated bounded binding count proves physical capacity even at eight units.
        available = None if active is None else 2 - active
        final = value.get('finalization', {})
        blocked = reason(value.get('admission_reason'))
        if runtime.closed:
            blocked = 'service_shutting_down'
        return {'service': 'tikrec', 'version': __version__, 'capabilities': [CAPABILITY],
            'capacity': 2, 'active_count': active, 'available_slots': available,
            'available': available is not None and available > 0,
            'shutting_down': runtime.closed, 'admission_available': value.get('available') is True,
            'admission_reason': blocked,
            'capture': {'capacity': 2, 'active_count': active, 'available_slots': available},
            'finalization': {'outstanding_units': number(final.get('outstanding_units')),
                'limit': 8, 'tasks': number(final.get('tasks')),
                'running': final.get('running') is True,
                'worker_available': runtime.started and not runtime.closed and runtime.paused is None
                    and final.get('running') is False,
                'paused_reason': reason(final.get('paused_reason')),
                'errors': number(final.get('errors')), 'errors_dropped': number(final.get('errors_dropped'))},
            'shutdown': shutdown_projection(runtime.shutdown_result)}

    def recordings(self):
        """Keep exactly two latest slot snapshots and at most eight outstanding tasks."""
        value = self.runtime.recordings()
        require(len(value['slots']) == 2 and len(value['finalization_sessions']) <= 8)
        slots = [{**session_projection(self.runtime, item), 'slot_id': item['slot_id']}
                 for item in value['slots']]
        require([item['slot_id'] for item in slots] == ['slot-1', 'slot-2'])
        # Empty admitted captures can retain an evidence unit without any assembly task.
        # Include every outstanding owner so slot reuse cannot hide those pinned facts.
        units = self.runtime.journal.status()['units']
        return {**self.health(), 'slots': slots, 'finalization_sessions':
            [session_projection(self.runtime, item) for item in value['finalization_sessions']],
            'outstanding_sessions': [self.session_status(unit['session']) for unit in units]}
