"""Allowlisted isolated monitoring projections; no arbitrary nested state escapes."""

from .creator_identity import validate_creator_handle
from .service_http_projection import number, path, reason
from .session_journal_types import identifier, room, require


MONITOR_REASONS = frozenset({
    'transient', 'unverifiable', 'unexpected', 'configuration_unavailable',
    'recording_slot_unavailable', 'output_directory_unconfigured',
    'output_name_unavailable', 'same_room_consumed', 'capacity_exhausted',
    'duplicate_live_owned', 'admission_unavailable', 'acceptance_unconfirmed',
    'automation_state_unavailable', 'automation_state_ambiguous', 'claim_clear_failed',
    'pending_claim_unavailable', 'claim_persistence_failed', 'start_failed',
    'earlier_start_failed', 'state_persistence_failed',
    'controller_state_unavailable', 'identity_unavailable', 'start_rejected_busy',
    'start_rejected', 'state_promotion_pending', 'prior_start_attempt_failed',
})


def category(value):
    """Retain documented fixed monitoring reasons, never diagnostic text."""
    return value if value in MONITOR_REASONS else reason(value)


def policy(value):
    """Bound admission/automation state and optional local artifact facts."""
    state = value.get('state')
    require(state in {'ready', 'blocked', 'skipped', 'not_applicable', 'armed',
        'suppressed', 'eligible', 'started', 'failed', 'not_selected'})
    result = {'state': state, 'reason': category(value.get('reason'))}
    for key in ('free_bytes',):
        if key in value:
            result[key] = number(value[key])
    for key in ('output_path', 'parts_directory'):
        if key in value:
            result[key] = path(value[key])
    if 'armed' in value:
        result['armed'] = value['armed'] is True
        room(value.get('consumed_room_id'))
        result['consumed_room_id'] = value.get('consumed_room_id')
    return result


def monitoring_projection(server):
    """Render explicitly supplied coordinator facts with current refusal categories."""
    value = server.automation.snapshot(server.monitor.snapshot())
    result = {key: number(value.get(key)) for key in ('poll_interval_seconds',
        'cycle_count', 'last_cycle_started_at', 'last_cycle_completed_at', 'minimum_free_bytes')}
    result.update({key: value.get(key) is True for key in ('running', 'cycle_in_progress')})
    configuration = value.get('configuration')
    if configuration is not None:
        require(configuration.get('state') in {'ok', 'unavailable'})
        result['configuration'] = {'state': configuration['state'],
            'reason': category(configuration.get('reason'))}
    creators = value.get('creators', [])
    require(len(creators) <= 100, 'monitoring projection bound exceeded')
    result['creators'] = []
    refusal = server.controller.health()['admission_reason']
    for item in creators:
        creator = validate_creator_handle(item['creator'])
        require(item['state'] in {'pending', 'live', 'offline', 'unknown'})
        room(item.get('room_id'))
        projected = {'creator': creator, 'state': item['state'], 'room_id': item.get('room_id'),
            'observed_at': number(item.get('observed_at')),
            'unknown_reason': category(item.get('unknown_reason'))}
        for key in ('admission', 'automation'):
            if key in item:
                projected[key] = policy(item[key])
        if refusal and item['state'] == 'live' and 'admission' in projected:
            projected['admission'].update(state='blocked', reason=refusal)
        result['creators'].append(projected)
    auto = value.get('automation', {})
    selected = auto.get('selected_creators', [])
    started = auto.get('started_recordings', [])
    # Duplicate refusals can visit more creators than the two accepted captures.
    require(len(selected) <= 100 and len(started) <= 2)
    selected = [validate_creator_handle(creator) for creator in selected]
    receipts = []
    for item in started:
        identifier(item['session_id'])
        receipts.append({'creator': validate_creator_handle(item['creator']),
            'session_id': item['session_id'], 'output_path': path(item.get('output_path'))})
    sole = receipts[0] if len(receipts) == 1 else {}
    result['automation'] = {'operational': auto.get('operational') is True,
        'blocked_reason': category(auto.get('blocked_reason')),
        'latest_cycle_count': number(auto.get('latest_cycle_count')),
        'selected_creators': selected, 'started_recordings': receipts,
        'selected_creator': selected[0] if len(selected) == 1 else None,
        'started_creator': sole.get('creator'), 'started_session_id': sole.get('session_id'),
        'started_output_path': sole.get('output_path')}
    return result
