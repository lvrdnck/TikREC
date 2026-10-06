"""Addressed immutable success evidence checks; historical records grant no authority."""

import json

from .session_journal_manifest import publication_view, steps_view
from .session_journal_owned_checks import receipt
from .session_journal_types import digest, encode, require

# Accepted seals bound artifacts to 4096: one frame-rate reader per FLV,
# one writer and three fixed validators, with one extra row to detect overflow.
MAX_CHILDREN = 4100


def manifest_view(connection, token):
    """Read the exact three committed control transitions."""
    row = connection.execute('SELECT * FROM manifest_preparations WHERE token=?', (token,)).fetchone()
    require(row is not None, 'successful manifest preparation missing')
    return {'operation': row['operation'], 'binding': json.loads(row['binding']),
            'steps': steps_view(connection, token)}


def child_facts(connection, token):
    """Read this attempt's bounded sequence, never all catalog history."""
    rows = connection.execute('SELECT * FROM child_launches WHERE token=? ORDER BY sequence LIMIT ?',
                              (token, MAX_CHILDREN + 1)).fetchall()
    return [{'launch': r['id'], 'sequence': r['sequence'],
        'identity': None if r['identity'] is None else json.loads(r['identity']),
        'exit': None if r['exit'] is None else json.loads(r['exit']), 'cleanup': r['cleanup'],
        'diagnostics_hash': None if r['diagnostics'] is None else digest(json.loads(r['diagnostics'])),
        'diagnostics_complete': r['diagnostics'] is not None and json.loads(r['diagnostics'])['complete']} for r in rows]


def check_binding(connection, row, binding):
    """Require installed/flushed controls, exact successful children and resource scope."""
    fields = {'session_id', 'token', 'owner', 'h_operation', 'h_revision', 'seal_hash', 'marker_hash'}
    require(type(binding) is dict and set(binding) == fields | {'manifest', 'publication', 'children', 'resources', 'claims'},
            'invalid completion release binding')
    require(all(binding[k] == row[k] for k in fields), 'release original ownership conflicts')
    manifest = manifest_view(connection, row['token'])
    require(binding['manifest'] == manifest and binding['publication'] == publication_view(connection, row['token'])
            and len(manifest['steps']) == 3 and manifest['steps'][-1]['phase'] == 'installed'
            and manifest['steps'][-1]['evidence']['required_flushed'], 'release lacks completed control chain')
    children = child_facts(connection, row['token'])
    require(binding['children'] == children and len(children) == row['sequence'] and 0 < len(children) <= MAX_CHILDREN
            and all(c['identity'] is not None and c['exit'] is not None
                and c['exit']['state'] == 'confirmed_exited' and c['exit']['active'] == 0
                and c['exit']['code'] == 0 and c['cleanup'] == 1 and c['diagnostics_hash'] is not None
                and c['diagnostics_complete'] for c in children), 'release execution evidence incomplete')
    from .session_journal_owned_checks import audit_child
    for child in connection.execute('SELECT * FROM child_launches WHERE token=? ORDER BY sequence LIMIT ?',
                                    (row['token'], MAX_CHILDREN + 1)):
        audit_child(connection, row, child)
    resources = binding['resources']
    session = connection.execute('SELECT * FROM sessions WHERE id=?', (row['session_id'],)).fetchone()
    intent = json.loads(session['intent'])
    claim = receipt(connection, row['claim_operation'], 'claim_owned')[1]
    require(binding['claims'] == {'unit': {'session': row['session_id'], 'kind': 'task'},
        'artifacts': [{'session': row['session_id'], 'kind': kind, 'identity': encode(intent[kind])}
                      for kind in ('output', 'parts')],
        'rooms': [] if session['room'] is None and session['expected_room'] is None else [session['room'] or session['expected_room']],
        'task_revision': claim['task_revision'], 'attempt': row['attempt']}, 'release lifetime claims conflict')
    task = connection.execute('SELECT * FROM tasks WHERE token=?', (row['token'],)).fetchone()
    require(task['attempt'] == row['attempt'] and task['session'] == row['session_id']
            and task['revision'] == claim['task_revision'] + (task['state'] == 'completed'),
            'release task revision conflicts')
    count = len(json.loads(session['seal'])['artifacts']) + 4
    expected = {f'input:{i}' for i in range(count)} | {'manifest:successor', 'scratch:workspace', 'lease'}
    expected |= {'scratch:' + a['name'] for a in row['scratch']['artifacts']}
    require(type(resources) is list and len(resources) == len(expected)
            and {r['key'] for r in resources} == expected, 'incomplete release resource scope')
    for resource in resources:
        require(type(resource) is dict and set(resource) == {'key', 'kind', 'evidence'}
                and resource['kind'] == ('lease' if resource['key'] == 'lease' else 'native')
                and type(resource['evidence']) is dict, 'invalid release resource evidence')
    from .session_journal_release_scope import check_scope
    check_scope(session, row, manifest, binding['publication'], resources)
    installed = manifest['steps'][-1]['evidence']
    stage = next(r['evidence'] for r in resources if r['key'] == 'manifest:successor')
    require(all(stage[k] == installed[k] for k in ('identity', 'size', 'stamp')),
            'release installed object conflicts')
    output = next(r['evidence'] for r in resources if r['key'] == 'scratch:candidate.mp4')
    require(all(output[k] == binding['publication']['evidence'][k] for k in ('identity', 'size', 'stamp')),
            'release output object conflicts')


def check_cleanup(binding, operation, evidence):
    """Cleanup observation is independent of preparation and contains every resource."""
    require(type(evidence) is dict and set(evidence) == {'preparation_operation', 'binding_hash', 'resources',
        'readers_complete', 'children_complete', 'cleanup_complete', 'diagnostics', 'diagnostics_dropped'}
        and evidence['preparation_operation'] == operation and evidence['binding_hash'] == digest(binding),
        'release cleanup binding conflicts')
    keys = [r['key'] for r in binding['resources']]
    results = evidence['resources']
    require(type(results) is list and [r.get('key') for r in results] == keys
            and all(set(r) == {'key', 'closed'} and type(r['closed']) is bool for r in results)
            and all(type(evidence[k]) is bool for k in ('readers_complete', 'children_complete', 'cleanup_complete'))
            and type(evidence['diagnostics']) is list and len(evidence['diagnostics']) <= 32
            and all(type(e) is str and len(e) <= 2048 for e in evidence['diagnostics'])
            and type(evidence['diagnostics_dropped']) is int and evidence['diagnostics_dropped'] >= 0,
            'invalid cleanup observations')
    complete = (all(r['closed'] for r in results) and evidence['readers_complete']
                and evidence['children_complete'] and not evidence['diagnostics'] and not evidence['diagnostics_dropped'])
    require(evidence['cleanup_complete'] is complete, 'cleanup success conflicts')


def audit_settlement(connection, row, *, historical=False):
    """Validate one addressed release chain; active audit never scans terminal history."""
    prep = connection.execute('SELECT * FROM release_preparations WHERE token=?', (row['token'],)).fetchone()
    if prep is None:
        require(not historical, 'terminal owned attempt lacks release history')
        return
    binding = json.loads(prep['binding'])
    check_binding(connection, row, binding)
    require(row['state'] == 'revoked', 'prepared attempt still has execution authority')
    previous = receipt(connection, binding['manifest']['steps'][-1]['operation'], 'manifest_step')[1]['revision']
    records = [(prep, 'prepare_release', 'binding', binding)]
    cleanup = connection.execute('SELECT * FROM release_cleanups WHERE token=?', (row['token'],)).fetchone()
    if cleanup is not None:
        evidence = json.loads(cleanup['evidence'])
        check_cleanup(binding, prep['operation'], evidence)
        records.append((cleanup, 'record_release_cleanup', 'evidence', evidence))
    terminal = connection.execute('SELECT * FROM release_results WHERE token=?', (row['token'],)).fetchone()
    require((terminal is not None) == historical, 'release terminal state conflicts')
    if terminal is not None:
        require(cleanup is not None and evidence['cleanup_complete'], 'terminal release lacks cleanup')
        terminal_evidence = json.loads(terminal['evidence'])
        require(terminal_evidence == {'preparation_operation': prep['operation'], 'cleanup_operation': cleanup['operation'],
            'binding_hash': digest(binding), 'cleanup_complete': True, 'returned_units': 1}, 'terminal release conflicts')
        records.append((terminal, 'settle_owned_success', 'evidence', terminal_evidence))
    for record, kind, field, value in records:
        op, result = receipt(connection, record['operation'], kind)
        require(result['previous_revision'] == previous and result['revision'] == previous + 1
                and result['token'] == row['token'] and result['owner'] == row['owner']
                and result['session_id'] == row['session_id'] and result[field] == value
                and result['operation'] == record['operation']
                and op['arguments_hash'] == digest([row['token'], row['owner'], result['previous_revision'], value]),
                'release receipt ordering conflicts')
        previous = result['revision']
