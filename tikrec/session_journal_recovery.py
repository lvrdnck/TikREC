"""Journal operations for explicit prepared-success recovery; no retry/adoption APIs."""

import json

from .session_journal_owned_view import owned_row
from .session_journal_recovery_authority import authorize
from .session_journal_recovery_checks import (check_recovery_authority, check_recovery_cleanup,
    check_recovery_proof)
from .session_journal_types import digest, encode, identifier, require
from .settlement_transaction import mutate


def _owner(connection, token):
    """Load only one attempt and its original seal for recovery checks."""
    row = owned_row(connection, token)
    require(row is not None, 'prepared attempt missing')
    session = connection.execute('SELECT seal FROM sessions WHERE id=?', (row['session_id'],)).fetchone()
    row['seal'] = json.loads(session['seal'])
    return row


class RecoveryOperations:
    """Append distinct generation proofs, then return capacity exactly once."""

    def begin_release_recovery(self, operation, token, session_id, authority, evidence, *, capability):
        """Fence stale normal callbacks before fresh attempt files are opened."""
        authorize(self, capability, 'begin_release_recovery', token, session_id, authority, evidence)
        identifier(token)
        identifier(session_id)
        identifier(authority)
        def action(connection):
            owner = _owner(connection, token)
            require(owner['session_id'] == session_id and owner['state'] == 'revoked',
                    'recovery does not address a revoked successful attempt')
            preparation = connection.execute('SELECT * FROM release_preparations WHERE token=?',
                                             (token,)).fetchone()
            normal = connection.execute('SELECT 1 FROM release_results WHERE token=?', (token,)).fetchone()
            recovered = connection.execute('SELECT 1 FROM release_recovery_results WHERE token=?',
                                            (token,)).fetchone()
            require(preparation is not None and normal is None and recovered is None,
                    'only a prepared, unsettled success may recover')
            task = connection.execute('SELECT * FROM tasks WHERE token=?', (token,)).fetchone()
            attempt = connection.execute('SELECT * FROM attempts WHERE token=?', (token,)).fetchone()
            session = connection.execute('SELECT * FROM sessions WHERE id=?', (session_id,)).fetchone()
            require(task['state'] == attempt['state'] == session['phase'] == 'running'
                    and task['session'] == session_id and task['attempt'] == owner['attempt']
                    and self.binding_claims(connection, session_id, json.loads(preparation['binding'])),
                    'recovery lost its outstanding task claims')
            binding = json.loads(preparation['binding'])
            check_recovery_authority(connection, owner, preparation, binding, 1, authority, evidence)
            prior = connection.execute('SELECT * FROM release_recovery_heads WHERE token=?', (token,)).fetchone()
            generation = 1 if prior is None else prior['generation'] + 1
            require(generation <= 32 and (prior is None or prior['state'] != 'released'),
                    'recovery generation limit or terminal fence reached')
            connection.execute('INSERT INTO release_recovery_authorities VALUES (?,?,?,?,?)',
                (token, generation, authority, encode(evidence), operation))
            if prior is None:
                connection.execute('INSERT INTO release_recovery_heads VALUES (?,?,?, ?,NULL,NULL,NULL)',
                    (token, generation, 'authorized', operation))
            else:
                connection.execute('UPDATE release_recovery_heads SET generation=?,state=?,authority_operation=?, '
                    'proof_operation=NULL,cleanup_operation=NULL,result_operation=NULL WHERE token=?',
                    (generation, 'authorized', operation, token))
            return {'session_id': session_id, 'token': token, 'generation': generation,
                'authority': authority, 'operation': operation,
                'preparation_operation': preparation['operation'],
                'binding_hash': digest(binding)}
        result = mutate(self, capability.readers, operation, 'begin_release_recovery',
            [token, session_id, authority, evidence], action)
        return result

    def record_release_recovery_proof(self, operation, token, generation, authority, evidence, *, capability):
        """Record a complete held-object proof without changing original attempt receipts."""
        authorize(self, capability, 'record_release_recovery_proof', token, generation, authority, evidence)
        def action(connection):
            owner = _owner(connection, token)
            preparation, binding = self._prepared(connection, token)
            head = self._recovery_head(connection, token, generation, authority, state='authorized')
            check_recovery_proof(owner, preparation, binding, authority, generation, evidence)
            connection.execute('INSERT INTO release_recovery_proofs VALUES (?,?,?,?)',
                (token, generation, encode(evidence), operation))
            connection.execute("UPDATE release_recovery_heads SET state='proved',proof_operation=? WHERE token=?",
                               (operation, token))
            return {'session_id': owner['session_id'], 'token': token, 'generation': generation,
                'authority': authority, 'operation': operation, 'evidence': evidence}
        return mutate(self, capability.readers, operation, 'record_release_recovery_proof',
            [token, generation, authority, evidence], action)

    def record_release_recovery_cleanup(self, operation, token, generation, authority, evidence, *, capability):
        """Persist every new handle close and every error, separately from old cleanup."""
        authorize(self, capability, 'record_release_recovery_cleanup', token, generation, authority, evidence)
        def action(connection):
            owner = _owner(connection, token)
            preparation, binding = self._prepared(connection, token)
            head = self._recovery_head(connection, token, generation, authority)
            proof = connection.execute('SELECT * FROM release_recovery_proofs WHERE token=? AND generation=?',
                                       (token, generation)).fetchone()
            proof_operation = None if proof is None else proof['operation']
            check_recovery_cleanup(owner, preparation, binding, generation, authority,
                                   proof_operation, evidence)
            connection.execute('INSERT INTO release_recovery_cleanups VALUES (?,?,?,?)',
                (token, generation, encode(evidence), operation))
            state = 'cleaned' if proof is not None and evidence['cleanup_complete'] else 'uncertain'
            connection.execute('UPDATE release_recovery_heads SET state=?,cleanup_operation=? WHERE token=?',
                               (state, operation, token))
            return {'session_id': owner['session_id'], 'token': token, 'generation': generation,
                'authority': authority, 'operation': operation, 'evidence': evidence, 'state': state}
        return mutate(self, capability.readers, operation, 'record_release_recovery_cleanup',
            [token, generation, authority, evidence], action)

    def settle_release_recovery(self, operation, token, generation, authority, evidence, *, capability):
        """Atomically terminalize verified recovery and delete its one exact task claim."""
        authorize(self, capability, 'settle_release_recovery', token, generation, authority, evidence)
        def action(connection):
            owner = _owner(connection, token)
            preparation, binding = self._prepared(connection, token)
            head = self._recovery_head(connection, token, generation, authority, state='cleaned')
            proof = connection.execute('SELECT * FROM release_recovery_proofs WHERE token=? AND generation=?',
                                       (token, generation)).fetchone()
            cleanup = connection.execute('SELECT * FROM release_recovery_cleanups WHERE token=? AND generation=?',
                                         (token, generation)).fetchone()
            require(proof is not None and cleanup is not None
                    and json.loads(cleanup['evidence'])['cleanup_complete'],
                    'confirmed fresh recovery cleanup required')
            proof_value, cleanup_value = json.loads(proof['evidence']), json.loads(cleanup['evidence'])
            expected = {'preparation_operation': preparation['operation'], 'binding_hash': digest(binding),
                'generation': generation, 'authority': authority,
                'authority_operation': head['authority_operation'], 'proof_operation': proof['operation'],
                'proof_hash': digest(proof_value),
                'cleanup_operation': cleanup['operation'],
                'cleanup_hash': digest(cleanup_value),
                'cleanup_complete': True, 'returned_units': 1}
            require(evidence == expected, 'recovery terminal evidence conflicts')
            task = connection.execute('SELECT * FROM tasks WHERE token=?', (token,)).fetchone()
            attempt = connection.execute('SELECT * FROM attempts WHERE token=?', (token,)).fetchone()
            session = connection.execute('SELECT * FROM sessions WHERE id=?', (owner['session_id'],)).fetchone()
            claims = binding['claims']
            require(task['state'] == attempt['state'] == session['phase'] == 'running'
                    and task['revision'] == claims['task_revision'] and task['session'] == owner['session_id']
                    and self.binding_claims(connection, owner['session_id'], binding),
                    'recovery accounting claims conflict')
            connection.execute('INSERT INTO release_recovery_results VALUES (?,?,?,?)',
                               (token, generation, encode(evidence), operation))
            connection.execute("UPDATE release_recovery_heads SET state='released',result_operation=? WHERE token=?",
                               (operation, token))
            connection.execute("UPDATE tasks SET state='completed',proof=?,revision=revision+1 WHERE token=?",
                               (encode(evidence), token))
            connection.execute("UPDATE attempts SET state='completed',proof=? WHERE token=?",
                               (encode(evidence), token))
            connection.execute("UPDATE sessions SET phase='completed',revision=revision+1 WHERE id=?",
                               (owner['session_id'],))
            require(connection.execute('DELETE FROM units WHERE session=? AND kind=?',
                (owner['session_id'], claims['unit']['kind'])).rowcount == 1,
                'exact recovery task unit missing')
            require(connection.execute('DELETE FROM artifacts WHERE session=?',
                (owner['session_id'],)).rowcount == 2, 'exact recovery artifact claims missing')
            require(connection.execute('DELETE FROM rooms WHERE session=?',
                (owner['session_id'],)).rowcount == len(claims['rooms']), 'exact recovery room claims missing')
            return {'session_id': owner['session_id'], 'token': token, 'generation': generation,
                'authority': authority, 'operation': operation, 'evidence': evidence,
                'state': 'released', 'returned_units': 1}
        return mutate(self, capability.readers, operation, 'settle_release_recovery',
            [token, generation, authority, evidence], action)

    @staticmethod
    def binding_claims(connection, session_id, binding):
        """Require all task, path, and room claims still belong to the prepared owner."""
        claims = binding['claims']
        units = [tuple(row) for row in connection.execute('SELECT session,kind FROM units WHERE session=?',
                                                          (session_id,))]
        artifacts = [tuple(row) for row in connection.execute(
            'SELECT kind,identity FROM artifacts WHERE session=? ORDER BY kind', (session_id,))]
        rooms = [row[0] for row in connection.execute('SELECT room FROM rooms WHERE session=? ORDER BY room',
                                                       (session_id,))]
        expected_artifacts = sorted((item['kind'], item['identity']) for item in claims['artifacts'])
        return (units == [(session_id, 'task')] and artifacts == expected_artifacts
                and rooms == sorted(claims['rooms']))

    def release_recovery(self, token):
        """Inspect addressed generation history without making files or authority live."""
        identifier(token)
        def read(connection):
            self._audit(connection)
            owner = owned_row(connection, token)
            if owner is None:
                return None
            head = connection.execute('SELECT * FROM release_recovery_heads WHERE token=?', (token,)).fetchone()
            if head is None:
                return None
            generation = head['generation']
            authority = connection.execute('SELECT * FROM release_recovery_authorities WHERE token=? AND generation=?',
                                           (token, generation)).fetchone()
            proof = connection.execute('SELECT * FROM release_recovery_proofs WHERE token=? AND generation=?',
                                       (token, generation)).fetchone()
            cleanup = connection.execute('SELECT * FROM release_recovery_cleanups WHERE token=? AND generation=?',
                                         (token, generation)).fetchone()
            result = connection.execute('SELECT * FROM release_recovery_results WHERE token=?', (token,)).fetchone()
            decode = lambda row, field: None if row is None else {**dict(row), field: json.loads(row[field])}
            return {'head': dict(head), 'authority': decode(authority, 'evidence'),
                'proof': decode(proof, 'evidence'), 'cleanup': decode(cleanup, 'evidence'),
                'result': decode(result, 'evidence')}
        return self._read(read)

    @staticmethod
    def _prepared(connection, token):
        preparation = connection.execute('SELECT * FROM release_preparations WHERE token=?', (token,)).fetchone()
        require(preparation is not None, 'prepared release missing')
        return preparation, json.loads(preparation['binding'])

    @staticmethod
    def _recovery_head(connection, token, generation, authority, *, state=None):
        head = connection.execute('SELECT * FROM release_recovery_heads WHERE token=?', (token,)).fetchone()
        record = connection.execute('SELECT authority FROM release_recovery_authorities '
            'WHERE token=? AND generation=?', (token, generation)).fetchone()
        require(head is not None and head['generation'] == generation and record is not None
                and record['authority'] == authority and (state is None or head['state'] == state),
                'stale or competing recovery authority')
        return head
