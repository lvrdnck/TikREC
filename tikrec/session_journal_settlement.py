"""Owned success release accounting; generic settlement and failure policy stay strict."""

import json

from .session_journal_owned import advance
from .session_journal_owned_view import owner_guard, owned_row
from .session_journal_settlement_checks import check_binding, check_cleanup, audit_settlement
from .session_journal_types import digest, encode, identifier, require
from .settlement_transaction import mutate
from .settlement_authority import authorize


class SettlementOperations:
    """Append exact completion/cleanup facts before atomic terminal capacity return."""

    def prepare_release(self, operation, token, owner, revision, binding, *, capability):
        """Revoke execution permanently while keeping running/countable ownership."""
        authorize(self, capability, 'prepare_release', token, owner, revision, binding)
        def action(connection):
            row = owner_guard(connection, token, owner, revision, launch=True)
            check_binding(connection, row, binding)
            step = connection.execute('SELECT result FROM operations WHERE id=?',
                (binding['manifest']['steps'][-1]['operation'],)).fetchone()
            require(json.loads(step[0])['revision'] == revision, 'release completion ordering conflicts')
            connection.execute('INSERT INTO release_preparations VALUES (?,?,?)', (token, encode(binding), operation))
            connection.execute("UPDATE attempt_owners SET state='revoked' WHERE token=?", (token,))
            return {**advance(connection, operation, row), 'binding': binding, 'state': 'cleanup_pending'}
        return mutate(self, capability.readers, operation, 'prepare_release', [token, owner, revision, binding], action)

    def record_release_cleanup(self, operation, token, owner, revision, evidence, *, capability):
        """Record confirmed and incomplete results separately without exposing capacity."""
        authorize(self, capability, 'record_release_cleanup', token, owner, revision, evidence)
        def action(connection):
            row = owner_guard(connection, token, owner, revision, cleanup=True)
            prep = connection.execute('SELECT * FROM release_preparations WHERE token=?', (token,)).fetchone()
            require(prep is not None and row['state'] == 'revoked', 'release cleanup authority missing')
            check_cleanup(json.loads(prep['binding']), prep['operation'], evidence)
            connection.execute('INSERT INTO release_cleanups VALUES (?,?,?)', (token, encode(evidence), operation))
            return {**advance(connection, operation, row), 'evidence': evidence,
                    'state': 'cleanup_confirmed' if evidence['cleanup_complete'] else 'cleanup_incomplete'}
        return mutate(self, capability.readers, operation, 'record_release_cleanup', [token, owner, revision, evidence], action)

    def settle_owned_success(self, operation, token, owner, revision, evidence, *, capability):
        """Atomically return only this task's outstanding unit and lifetime claims."""
        authorize(self, capability, 'settle_owned_success', token, owner, revision, evidence)
        def action(connection):
            row = owner_guard(connection, token, owner, revision, cleanup=True)
            prep = connection.execute('SELECT * FROM release_preparations WHERE token=?', (token,)).fetchone()
            cleanup = connection.execute('SELECT * FROM release_cleanups WHERE token=?', (token,)).fetchone()
            require(prep is not None and cleanup is not None and row['state'] == 'revoked'
                    and json.loads(cleanup['evidence'])['cleanup_complete'], 'confirmed cleanup required')
            expected = {'preparation_operation': prep['operation'], 'cleanup_operation': cleanup['operation'],
                'binding_hash': digest(json.loads(prep['binding'])), 'cleanup_complete': True, 'returned_units': 1}
            require(evidence == expected, 'terminal success proof conflicts')
            connection.execute('INSERT INTO release_results VALUES (?,?,?)', (token, encode(evidence), operation))
            result = {**advance(connection, operation, row), 'evidence': evidence, 'state': 'released', 'returned_units': 1}
            connection.execute("UPDATE tasks SET state='completed',proof=?,revision=revision+1 WHERE token=?",
                               (encode(evidence), token))
            connection.execute("UPDATE attempts SET state='completed',proof=? WHERE token=?", (encode(evidence), token))
            connection.execute("UPDATE sessions SET phase='completed',revision=revision+1 WHERE id=?", (row['session_id'],))
            self._inject('settle_owned_success', 'after_terminal')
            require(connection.execute("DELETE FROM units WHERE session=? AND kind='task'",
                (row['session_id'],)).rowcount == 1, 'exact task unit missing')
            self._inject('settle_owned_success', 'after_unit_release')
            require(connection.execute('DELETE FROM artifacts WHERE session=?', (row['session_id'],)).rowcount == 2,
                    'exact task artifact claims missing')
            require(connection.execute('DELETE FROM rooms WHERE session=?', (row['session_id'],)).rowcount ==
                len(json.loads(prep['binding'])['claims']['rooms']), 'exact task room claims missing')
            self._inject('settle_owned_success', 'after_claim_release')
            return result
        return mutate(self, capability.readers, operation, 'settle_owned_success', [token, owner, revision, evidence], action)

    def settlement(self, token):
        """Inspect only committed addressed facts; never infer cleanup after restart."""
        identifier(token)
        def read(connection):
            self._audit(connection)
            row = owned_row(connection, token)
            if row is None:
                return None
            terminal = connection.execute('SELECT 1 FROM release_results WHERE token=?', (token,)).fetchone()
            from .session_journal_owned_checks import audit_owner
            audit_owner(connection, token, historical=terminal is not None)
            records = {}
            for name, table, field in [('preparation', 'release_preparations', 'binding'),
                ('cleanup', 'release_cleanups', 'evidence'), ('result', 'release_results', 'evidence')]:
                value = connection.execute(f'SELECT * FROM {table} WHERE token=?', (token,)).fetchone()
                records[name] = None if value is None else {**dict(value), field: json.loads(value[field])}
            if records['preparation'] is None:
                return None
            state = 'released' if terminal else 'cleanup_pending' if records['cleanup'] is None else (
                'cleanup_confirmed' if records['cleanup']['evidence']['cleanup_complete'] else 'cleanup_incomplete')
            return {**records, 'state': state}
        return self._read(read)
