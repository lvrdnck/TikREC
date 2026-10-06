"""Addressed audits for restart authority, fresh proof, cleanup, and settlement."""

import json

from .session_journal_owned_checks import receipt
from .session_journal_types import digest, require, sha256


def _identity(value):
    require(type(value) is dict and set(value) == {'volume', 'components'}
            and type(value['volume']) is str and type(value['components']) is list
            and all(type(part) is str for part in value['components']), 'invalid recovery identity')


def _binding(connection, token):
    prep = connection.execute('SELECT * FROM release_preparations WHERE token=?', (token,)).fetchone()
    require(prep is not None, 'prepared release is required')
    return prep, json.loads(prep['binding'])


def _cleanup_snapshot(connection, token):
    row = connection.execute('SELECT * FROM release_cleanups WHERE token=?', (token,)).fetchone()
    if row is None:
        return None
    evidence = json.loads(row['evidence'])
    return {'operation': row['operation'], 'evidence_hash': digest(evidence),
            'cleanup_complete': evidence['cleanup_complete']}


def check_recovery_authority(connection, owner, preparation, binding, generation, authority, evidence):
    """Bind each fresh generation to the known catalog and the exact prepared release."""
    keys = {'schema_version', 'catalog_id', 'catalog_native', 'catalog_stamp', 'state_native',
        'state_stamp', 'owner_lock', 'media_native', 'writer_lease', 'preparation_operation',
        'binding_hash', 'original_cleanup', 'retired'}
    require(type(evidence) is dict and set(evidence) == keys and evidence['schema_version'] == 1,
            'invalid recovery authority evidence')
    metadata = connection.execute('SELECT id,version FROM catalog LIMIT 2').fetchall()
    require(len(metadata) == 1 and evidence['catalog_id'] == metadata[0]['id']
            and evidence['preparation_operation'] == preparation['operation']
            and evidence['binding_hash'] == digest(binding)
            and evidence['original_cleanup'] == _cleanup_snapshot(connection, owner['token']),
            'recovery authority is not bound to this prepared release')
    for key in ('catalog_native', 'state_native', 'media_native'):
        _identity(evidence[key])
    require(type(evidence['catalog_stamp']) is str and type(evidence['state_stamp']) is str,
            'recovery catalog owner proof missing')
    lock, lease = evidence['owner_lock'], evidence['writer_lease']
    require(type(lock) is dict and set(lock) == {'mode', 'slot', 'root', 'identity'}
            and lock['mode'] == 'retention' and type(lock['slot']) is int
            and type(lock['identity']) is list and len(lock['identity']) == 5
            and type(lease) is dict and set(lease) == {'mode', 'slot', 'identity', 'root'}
            and lease['mode'] == 'writer' and type(lease['slot']) is int
            and 0 <= lease['slot'] < 64 and type(lease['identity']) is list
            and len(lease['identity']) == 5, 'recovery root lease proof missing')
    root = next(resource['evidence']['path'] for resource in binding['resources']
                if resource['key'] == 'input:0')
    require(lock['root'] != root and lease['root'] == root
            and evidence['retired'] == {'catalog_exclusive': True, 'local_attempt_absent': True,
                                       'original_owner_revoked': True},
            'old release ownership is not retired or safely excluded')


def expected_inventory(owner, binding):
    """Return only the prepared attempt's exact post-install namespaces."""
    seal = owner['seal']
    manifest = binding['manifest']
    parts = [a['identity']['components'][-1] for a in seal['artifacts']]
    parts = [manifest['binding']['namespace']['history'] if n == 'session.json' else n for n in parts]
    parts.extend(('session.json', 'finalization-owner.json'))
    scratch = [a['name'] for a in owner['scratch']['artifacts'] if a['name'] != 'candidate.mp4']
    return sorted(n.casefold() for n in parts), sorted(n.casefold() for n in scratch)


def _expected_controls(owner, binding):
    seal = owner['seal']
    controls = []
    for index, artifact in enumerate(seal['artifacts'], 3):
        if artifact['control_hash'] is not None:
            controls.append({'key': f'input:{index}', 'sha256': artifact['control_hash']})
    controls.append({'key': f'input:{len(seal["artifacts"]) + 3}', 'sha256': owner['marker_hash']})
    controls.append({'key': 'manifest:successor', 'sha256': binding['manifest']['binding']['successor']['sha256']})
    return controls


def check_recovery_proof(owner, preparation, binding, authority, generation, evidence):
    """Check fresh native observations against the immutable publication/control chain."""
    keys = {'schema_version', 'session_id', 'token', 'generation', 'authority',
        'preparation_operation', 'binding_hash', 'resources', 'controls', 'output_sha256',
        'parts_inventory', 'scratch_inventory'}
    require(type(evidence) is dict and set(evidence) == keys and evidence['schema_version'] == 1
            and evidence['token'] == owner['token'] and evidence['session_id'] == owner['session_id']
            and evidence['generation'] == generation and evidence['authority'] == authority
            and evidence['preparation_operation'] == preparation['operation']
            and evidence['binding_hash'] == digest(binding), 'recovery proof binding conflicts')
    original = binding['resources']
    resources = evidence['resources']
    require(type(resources) is list and len(resources) == len(original), 'recovery resource proof incomplete')
    for before, after in zip(original, resources, strict=True):
        require(type(after) is dict and set(after) == {'key', 'kind', 'evidence'}
                and after['key'] == before['key'] and after['kind'] == before['kind']
                and type(after['evidence']) is dict, 'recovery resource order conflicts')
        expected, actual = before['evidence'], after['evidence']
        if before['kind'] == 'native':
            require(set(actual) == {'path', 'identity', 'size', 'stamp'}
                    and actual['path'] == expected['path'] and actual['identity'] == expected['identity']
                    and type(actual['size']) is int and type(actual['stamp']) is str,
                    'recovery native resource identity conflicts')
            if before['key'] in {'input:0', 'input:2', 'scratch:workspace'}:
                require(actual['stamp'].split(':')[:2] == expected['stamp'].split(':')[:2],
                        'recovery directory identity changed')
            else:
                require(actual['size'] == expected['size'] and actual['stamp'] == expected['stamp'],
                        'recovery file seal changed')
        else:
            lease = actual
            require(set(lease) == {'mode', 'slot', 'identity', 'root'} and lease['mode'] == 'writer'
                    and type(lease['slot']) is int and 0 <= lease['slot'] < 64
                    and lease['root'] == expected['root'] and len(lease['identity']) == 5,
                    'fresh recovery lease conflicts')
    publication = binding['publication']['evidence']
    require(evidence['output_sha256'] == publication['sha256']
            and evidence['controls'] == _expected_controls(owner, binding),
            'recovery media or control hash conflicts')
    parts, scratch = expected_inventory(owner, binding)
    require(evidence['parts_inventory'] == parts and evidence['scratch_inventory'] == scratch,
            'recovery namespace inventory conflicts')


def check_recovery_cleanup(owner, preparation, binding, generation, authority, proof_operation, evidence):
    """Keep each generation's new handle teardown distinct from original receipts."""
    keys = {'schema_version', 'session_id', 'token', 'generation', 'authority',
        'preparation_operation', 'binding_hash', 'proof_operation', 'resources',
        'cleanup_complete', 'diagnostics', 'diagnostics_dropped'}
    require(type(evidence) is dict and set(evidence) == keys and evidence['schema_version'] == 1
            and evidence['token'] == owner['token'] and evidence['session_id'] == owner['session_id']
            and evidence['generation'] == generation and evidence['authority'] == authority
            and evidence['preparation_operation'] == preparation['operation']
            and evidence['binding_hash'] == digest(binding)
            and evidence['proof_operation'] == proof_operation,
            'recovery cleanup binding conflicts')
    resources = evidence['resources']
    expected = [r['key'] for r in binding['resources']]
    require(type(resources) is list and [r.get('key') for r in resources] == expected
            and all(set(r) == {'key', 'acquired', 'closed'}
                and type(r['acquired']) is bool and type(r['closed']) is bool for r in resources),
            'recovery cleanup resource inventory conflicts')
    require(type(evidence['cleanup_complete']) is bool and type(evidence['diagnostics']) is list
            and len(evidence['diagnostics']) <= 32 and all(type(v) is str and len(v) <= 2048
                for v in evidence['diagnostics']) and type(evidence['diagnostics_dropped']) is int
            and evidence['diagnostics_dropped'] >= 0, 'invalid recovery cleanup observation')
    complete = (all(not r['acquired'] or r['closed'] for r in resources)
                and not evidence['diagnostics'] and not evidence['diagnostics_dropped'])
    require(evidence['cleanup_complete'] is complete and (proof_operation is None or all(
        r['acquired'] for r in resources)), 'recovery cleanup is not confirmed')


def audit_recovery(connection, owner, *, historical=False):
    """Validate one addressed recovery sequence; never scan terminal catalog history."""
    head = connection.execute('SELECT * FROM release_recovery_heads WHERE token=?', (owner['token'],)).fetchone()
    terminal = connection.execute('SELECT * FROM release_recovery_results WHERE token=?', (owner['token'],)).fetchone()
    require((terminal is not None) == historical or not historical and terminal is None,
            'recovery terminal state conflicts')
    authorities = connection.execute('SELECT * FROM release_recovery_authorities WHERE token=? '
        'ORDER BY generation LIMIT 33', (owner['token'],)).fetchall()
    require(len(authorities) <= 32 and (bool(authorities) == (head is not None)),
            'recovery generation history is unbounded or incomplete')
    if not authorities:
        require(terminal is None, 'recovered terminal lacks authority history')
        return
    preparation, binding = _binding(connection, owner['token'])
    proof_rows = {r['generation']: r for r in connection.execute(
        'SELECT * FROM release_recovery_proofs WHERE token=?', (owner['token'],))}
    cleanup_rows = {r['generation']: r for r in connection.execute(
        'SELECT * FROM release_recovery_cleanups WHERE token=?', (owner['token'],))}
    latest = None
    session = connection.execute('SELECT seal FROM sessions WHERE id=?', (owner['session_id'],)).fetchone()
    owner['seal'] = json.loads(session['seal'])
    for expected, record in enumerate(authorities, 1):
        require(record['generation'] == expected, 'recovery generation sequence has a gap')
        evidence = json.loads(record['evidence'])
        check_recovery_authority(connection, owner, preparation, binding, expected, record['authority'], evidence)
        operation, result = receipt(connection, record['operation'], 'begin_release_recovery')
        expected_result = {'session_id': owner['session_id'], 'token': owner['token'],
            'generation': expected, 'authority': record['authority'], 'operation': record['operation'],
            'preparation_operation': preparation['operation'], 'binding_hash': digest(binding)}
        require(result == expected_result and operation['arguments_hash'] == digest(
            [owner['token'], owner['session_id'], record['authority'], evidence]),
            'recovery authority receipt conflicts')
        proof, cleanup = proof_rows.get(expected), cleanup_rows.get(expected)
        proof_value = cleanup_value = None
        if proof is not None:
            proof_value = json.loads(proof['evidence'])
            check_recovery_proof(owner, preparation, binding, record['authority'], expected, proof_value)
            operation, result = receipt(connection, proof['operation'], 'record_release_recovery_proof')
            require(result['evidence'] == proof_value and result['generation'] == expected
                    and operation['arguments_hash'] == digest(
                        [owner['token'], expected, record['authority'], proof_value]),
                    'recovery proof receipt conflicts')
        if cleanup is not None:
            cleanup_value = json.loads(cleanup['evidence'])
            check_recovery_cleanup(owner, preparation, binding, expected, record['authority'],
                None if proof is None else proof['operation'], cleanup_value)
            operation, result = receipt(connection, cleanup['operation'], 'record_release_recovery_cleanup')
            require(result['evidence'] == cleanup_value and result['generation'] == expected
                    and operation['arguments_hash'] == digest(
                        [owner['token'], expected, record['authority'], cleanup_value]),
                    'recovery cleanup receipt conflicts')
        latest = (record, proof, cleanup, proof_value, cleanup_value)
    current, proof, cleanup, proof_value, cleanup_value = latest
    require(head['generation'] == current['generation'] and head['authority_operation'] == current['operation']
            and head['proof_operation'] == (None if proof is None else proof['operation'])
            and head['cleanup_operation'] == (None if cleanup is None else cleanup['operation'])
            and head['result_operation'] == (None if terminal is None else terminal['operation']),
            'recovery fencing head conflicts')
    expected_state = ('released' if terminal is not None else 'uncertain' if cleanup is not None
        and not cleanup_value['cleanup_complete'] or cleanup is not None and proof is None else
        'cleaned' if cleanup is not None else 'proved' if proof is not None else 'authorized')
    require(head['state'] == expected_state, 'recovery fencing state conflicts')
    if terminal is not None:
        require(proof is not None and cleanup is not None and cleanup_value['cleanup_complete'],
                'recovery terminal lacks verified proof and cleanup')
        value = json.loads(terminal['evidence'])
        require(value == {'preparation_operation': preparation['operation'], 'binding_hash': digest(binding),
            'generation': current['generation'], 'authority': current['authority'],
            'authority_operation': current['operation'], 'proof_operation': proof['operation'],
            'proof_hash': digest(proof_value), 'cleanup_operation': cleanup['operation'],
            'cleanup_hash': digest(cleanup_value), 'cleanup_complete': True, 'returned_units': 1},
            'recovery terminal receipt conflicts')
        operation, result = receipt(connection, terminal['operation'], 'settle_release_recovery')
        require(result['evidence'] == value and operation['arguments_hash'] == digest(
            [owner['token'], current['generation'], current['authority'], value]),
            'recovery terminal operation conflicts')
        task = connection.execute('SELECT * FROM tasks WHERE token=?', (owner['token'],)).fetchone()
        attempt = connection.execute('SELECT * FROM attempts WHERE token=?', (owner['token'],)).fetchone()
        session = connection.execute('SELECT * FROM sessions WHERE id=?', (owner['session_id'],)).fetchone()
        require(task['state'] == attempt['state'] == session['phase'] == 'completed'
                and task['proof'] == attempt['proof'] == terminal['evidence']
                and connection.execute('SELECT 1 FROM units WHERE session=?', (owner['session_id'],)).fetchone() is None
                and connection.execute('SELECT 1 FROM artifacts WHERE session=?', (owner['session_id'],)).fetchone() is None
                and connection.execute('SELECT 1 FROM rooms WHERE session=?', (owner['session_id'],)).fetchone() is None,
                'recovered release accounting conflicts')
