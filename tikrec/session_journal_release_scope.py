"""Exact resource namespace/evidence binding to immutable capture and control history."""

import json
from pathlib import Path

from .session_journal_types import require
from .capture_handoff_marker import MARKER_NAME


def check_scope(session, owner, manifest, publication, resources):
    """Reject omitted, foreign or contradictory original resource declarations."""
    intent, seal = json.loads(session['intent']), json.loads(session['seal'])
    by_key = {r['key']: r['evidence'] for r in resources}
    native = [r['evidence'] for r in resources if r['kind'] == 'native']
    for value in native:
        require(set(value) == {'path', 'identity', 'size', 'stamp'} and type(value['path']) is str
                and Path(value['path']).is_absolute() and type(value['size']) is int and value['size'] >= 0
                and type(value['stamp']) is str and len(value['stamp']) <= 256
                and type(value['identity']) is dict and set(value['identity']) == {'volume', 'components'},
                'invalid native release scope')
    def identity(key, expected, path):
        require(by_key[key]['identity'] == expected and by_key[key]['path'] == path,
                'foreign native release resource')
    root, parts = intent['root'], intent['parts']
    root_path = str(Path(intent['output_path']).parent)
    identity('input:0', root, root_path)
    identity('input:1', {'volume': root['volume'], 'components': [*root['components'], '.tikrec-lifecycle.lock']},
             str(Path(root_path) / '.tikrec-lifecycle.lock'))
    identity('input:2', parts, intent['parts_path'])
    for index, artifact in enumerate(seal['artifacts'], 3):
        expected = artifact['identity']
        if expected['components'][-1] == 'session.json':
            expected = {'volume': parts['volume'], 'components': [*parts['components'], manifest['binding']['namespace']['history']]}
        value = by_key[f'input:{index}']
        identity(f'input:{index}', expected, str(Path(intent['parts_path']) / expected['components'][-1]))
        require(value['size'] == artifact['size'] and value['stamp'] == artifact['stamp'], 'release input seal changed')
    marker = {'volume': parts['volume'], 'components': [*parts['components'], MARKER_NAME]}
    identity(f'input:{len(seal["artifacts"]) + 3}', marker, str(Path(intent['parts_path']) / MARKER_NAME))
    identity('manifest:successor', manifest['steps'][-1]['evidence']['identity'], str(Path(intent['parts_path']) / 'session.json'))
    scratch = owner['scratch']
    identity('scratch:workspace', scratch['workspace_identity'], scratch['intent']['workspace_path'])
    require(by_key['scratch:workspace']['stamp'].split(':')[:2] == scratch['workspace_stamp'].split(':')[:2],
            'release workspace identity changed')
    for artifact in scratch['artifacts']:
        key = 'scratch:' + artifact['name']
        expected = json.loads(artifact['identity'])
        path = str(Path(scratch['intent']['workspace_path']) / artifact['name'])
        if artifact['name'] == 'candidate.mp4':
            expected, path = publication['evidence']['identity'], intent['output_path']
        identity(key, expected, path)
        require(by_key[key]['size'] == artifact['size'] and by_key[key]['stamp'] == artifact['stamp'],
                'release scratch artifact changed')
    lease = by_key['lease']
    require(set(lease) == {'mode', 'slot', 'identity', 'root'} and lease['mode'] == 'writer'
            and type(lease['slot']) is int and 0 <= lease['slot'] < 64
            and lease['root'] == root_path and type(lease['identity']) is list and len(lease['identity']) == 5,
            'release lease scope conflicts')
