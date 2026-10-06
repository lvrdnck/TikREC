"""Audit immutable control chains without filesystem access or restart adoption."""

import json

from .session_journal_manifest import check_binding, check_step, steps_view, PHASES
from .session_journal_owned_checks import receipt
from .session_journal_types import digest, require


def audit_manifest(connection, owner):
    """Prove original H/publication binding and exact append-only operation ordering."""
    prep = connection.execute('SELECT * FROM manifest_preparations WHERE token=?', (owner['token'],)).fetchone()
    if prep is None:
        return
    binding = json.loads(prep['binding'])
    check_binding(connection, owner, binding)
    op, result = receipt(connection, prep['operation'], 'prepare_manifest')
    publication = connection.execute('SELECT result FROM operations WHERE id=?',
        (binding['publication']['result_operation'],)).fetchone()
    previous = json.loads(publication[0])['revision']
    require(result.get('binding') == binding and result.get('state') == 'prepared', 'manifest preparation receipt conflicts')
    records = [(op, result, prep['operation'], [binding])]
    steps = steps_view(connection, owner['token'])
    for index, step in enumerate(steps):
        require(step['phase'] == PHASES[index], 'manifest durable phases omitted')
        check_step(binding, prep['operation'], step['phase'], step['evidence'], steps[:index])
        op, result = receipt(connection, step['operation'], 'manifest_step')
        require(result.get('evidence') == step['evidence'] and result.get('phase') == step['phase'],
                'manifest result receipt conflicts')
        records.append((op, result, step['operation'], [step['phase'], step['evidence']]))
    for op, result, operation, tail in records:
        require(result['previous_revision'] == previous and result['revision'] == previous + 1
                and result['token'] == owner['token'] and result['owner'] == owner['owner']
                and result['session_id'] == owner['session_id'] and result['operation'] == operation
                and op['arguments_hash'] == digest([owner['token'], owner['owner'], previous, *tail]),
                'manifest receipt ordering conflicts')
        previous = result['revision']
