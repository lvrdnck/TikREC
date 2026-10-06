"""Append-only control authority and intermediate results, never terminal settlement."""

import json
from contextlib import contextmanager

from .manifest_successor_values import successor_bytes, unpacked
from .session_journal_owned import advance
from .session_journal_owned_view import owner_guard
from .session_journal_publication import validation_view
from .session_journal_types import digest, encode, identifier, require

PHASES = ('staged', 'preserved', 'installed')


def publication_view(connection, token):
    """Read the exact committed chain without inferring fresh filesystem authority."""
    p = connection.execute("SELECT * FROM publication_preparations WHERE token=?", (token,)).fetchone()
    r = connection.execute("SELECT * FROM publication_results WHERE token=?", (token,)).fetchone()
    require(p is not None and r is not None, "observed publication missing")
    return {"binding": json.loads(p['binding']), "operation": p['operation'],
            "result_operation": r['operation'], "evidence": json.loads(r['evidence'])}


def check_binding(connection, row, binding):
    """Bind recoverable predecessor, exact successor and declared namespaces to original H."""
    require(type(binding) is dict and set(binding) == {'session_id', 'token', 'owner', 'h_operation',
        'h_revision', 'seal_hash', 'marker_hash', 'publication', 'predecessor', 'successor', 'namespace'},
        "invalid manifest preparation")
    for key in ('session_id', 'token', 'owner', 'h_operation', 'h_revision', 'seal_hash', 'marker_hash'):
        require(binding[key] == row[key], "manifest original owner conflicts")
    require(binding['publication'] == publication_view(connection, row['token']), "manifest publication conflicts")
    session = dict(connection.execute("SELECT * FROM sessions WHERE id=?", (row['session_id'],)).fetchone())
    session['intent'], session['seal'] = json.loads(session['intent']), json.loads(session['seal'])
    original = next(a for a in session['seal']['artifacts'] if a['identity']['components'][-1] == 'session.json')
    predecessor, successor, namespace = binding['predecessor'], binding['successor'], binding['namespace']
    old, new = unpacked(predecessor), unpacked(successor)
    require(set(predecessor) == {'bytes', 'sha256', 'identity', 'size', 'stamp'}
            and predecessor['identity'] == original['identity'] and predecessor['size'] == original['size']
            and predecessor['stamp'] == original['stamp'] and predecessor['sha256'] == original['control_hash']
            and len(old) == predecessor['size'] and set(successor) == {'bytes', 'sha256'},
            "manifest predecessor seal conflicts")
    report = validation_view(connection, row['token'])['evidence']['report']
    # Accepted candidate evidence encodes copy's not_checked as unknown;
    # retain the established public classification without rewriting that seal.
    status = report['assembly_input_decode']['status']
    copy = any(a['name'] == 'concat.ffconcat' for a in row['scratch']['intent']['artifacts'])
    require((status == 'not_checked') == copy, 'manifest copy/decoder classification conflicts')
    require(('unknown' if status == 'not_checked' else status) ==
            row['scratch']['candidate']['execution']['input_decode'],
            'manifest assembly decoding classification conflicts')
    require(new == successor_bytes(old, session, report), "manifest successor semantics conflict")
    require(namespace == {'parent': session['intent']['parts'], 'manifest': 'session.json',
        'history': f'.tikrec-manifest-{row["token"]}.original.json',
        'stage': f'.tikrec-manifest-{row["token"]}.successor.json'}, "manifest namespace conflicts")


def check_step(binding, preparation, phase, evidence, previous):
    """Require complete ordered facts; intent and staging never imply installation."""
    require(phase in PHASES and type(evidence) is dict and set(evidence) == {
        'state', 'preparation_operation', 'binding_hash', 'identity', 'size', 'stamp', 'sha256', 'required_flushed'},
        "invalid manifest step")
    name = binding['namespace']['history' if phase == 'preserved' else 'stage' if phase == 'staged' else 'manifest']
    parent = binding['namespace']['parent']
    identity = {'volume': parent['volume'], 'components': [*parent['components'], name]}
    data = binding['predecessor' if phase == 'preserved' else 'successor']
    require(evidence['state'] == phase and evidence['preparation_operation'] == preparation
            and evidence['binding_hash'] == digest(binding) and evidence['identity'] == identity
            and evidence['size'] == len(unpacked(data)) and evidence['sha256'] == data['sha256']
            and type(evidence['stamp']) is str and len(evidence['stamp']) <= 256
            and evidence['required_flushed'] is (phase != 'preserved'), "manifest observed proof conflicts")
    stamp = evidence['stamp'].split(':')
    require(len(stamp) == 4 and all(x and all(c in '0123456789abcdef' for c in x) for x in stamp)
            and int(stamp[2], 16) == evidence['size']
            and stamp[0] == binding['predecessor']['stamp'].split(':')[0], 'invalid control native stamp')
    if phase == 'preserved':
        require(evidence['stamp'] == binding['predecessor']['stamp'], "original manifest stamp changed")
    if phase == 'installed':
        require(previous[0]['evidence']['stamp'] == evidence['stamp'], "installed staging object changed")


def steps_view(connection, token):
    """Project at most three committed intermediate proofs in protocol order."""
    rows = {r['phase']: dict(r) for r in connection.execute("SELECT * FROM manifest_steps WHERE token=?", (token,))}
    return [{**rows[p], 'evidence': json.loads(rows[p]['evidence'])} for p in PHASES if p in rows]


class ManifestOperations:
    """Records never reconstruct live control/write authority after reopening."""

    def prepare_manifest(self, operation, token, owner, revision, binding):
        """Commit original bytes and the intended successor before any new artifact."""
        def action(connection):
            row = owner_guard(connection, token, owner, revision, launch=True)
            check_binding(connection, row, binding)
            result = connection.execute("SELECT result FROM operations WHERE id=?",
                (binding['publication']['result_operation'],)).fetchone()
            require(json.loads(result[0])['revision'] == revision, "manifest publication ordering conflicts")
            connection.execute("INSERT INTO manifest_preparations VALUES (?,?,?)", (token, encode(binding), operation))
            return {**advance(connection, operation, row), 'binding': binding, 'state': 'prepared'}
        return self._mutate(operation, 'prepare_manifest', [token, owner, revision, binding], action)

    def manifest_step(self, operation, token, owner, revision, phase, evidence):
        """Append verified staging/preservation/installation separately, retaining all units."""
        def action(connection):
            row = owner_guard(connection, token, owner, revision, launch=True)
            prep = connection.execute("SELECT * FROM manifest_preparations WHERE token=?", (token,)).fetchone()
            require(prep is not None, "manifest preparation absent")
            prior = steps_view(connection, token)
            require(len(prior) < 3 and phase == PHASES[len(prior)], "manifest phase ordering conflicts")
            check_step(json.loads(prep['binding']), prep['operation'], phase, evidence, prior)
            connection.execute("INSERT INTO manifest_steps VALUES (?,?,?,?)", (token, phase, encode(evidence), operation))
            return {**advance(connection, operation, row), 'phase': phase, 'evidence': evidence}
        return self._mutate(operation, 'manifest_step', [token, owner, revision, phase, evidence], action)

    @contextmanager
    def manifest_fence(self, token, owner, revision, operation, binding_hash, step_count):
        """Serialize narrow native authority with durable revocation, without callbacks/scans."""
        connection = self._connect()
        try:
            connection.execute('BEGIN')
            owner_guard(connection, token, owner, revision, launch=True)
            prep = connection.execute("SELECT * FROM manifest_preparations WHERE token=?", (token,)).fetchone()
            require(prep is not None and prep['operation'] == operation
                    and digest(json.loads(prep['binding'])) == binding_hash
                    and len(steps_view(connection, token)) == step_count, "stale manifest authority")
            yield
        finally:
            connection.rollback()
            connection.close()

    def manifest_completion(self, token):
        """Read committed facts only; no paths, inferred success or repeat-write permission."""
        identifier(token)
        def read(connection):
            self._audit(connection)
            prep = connection.execute("SELECT * FROM manifest_preparations WHERE token=?", (token,)).fetchone()
            return None if prep is None else {'binding': json.loads(prep['binding']),
                'operation': prep['operation'], 'steps': steps_view(connection, token)}
        return self._read(read)
