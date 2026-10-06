"""Narrow release transactions retain exact SQLite connections through teardown faults."""

from .session_journal_manifest_fence import ManifestFenceConnection
from .session_journal_receipts import validate_operation_receipt
from .session_journal_types import JournalConflict, JournalUncertain, digest, encode, identifier


def mutate(journal, readers, operation, kind, arguments, action):
    """Preserve first failure; independently close on the original SQLite thread."""
    identifier(operation)
    connection, retained, primary, committing, result = None, None, None, False, None
    try:
        connection = journal._connect()
        retained = ManifestFenceConnection(connection)
        readers.append(retained)
        connection.execute('BEGIN IMMEDIATE')
        journal._audit(connection)
        prior = connection.execute('SELECT * FROM operations WHERE id=?', (operation,)).fetchone()
        if prior is not None:
            if prior['kind'] != kind or prior['arguments_hash'] != digest(arguments):
                raise JournalConflict('release operation identity conflicts')
            result = validate_operation_receipt(connection, prior)
        else:
            journal._inject(kind, 'after_begin')
            result = action(connection)
            journal._inject(kind, 'after_writes')
            connection.execute('INSERT INTO operations VALUES (?,?,?,?)',
                (operation, kind, digest(arguments), encode(result)))
            journal._audit(connection)
            journal._inject(kind, 'before_commit')
            committing = True
            connection.commit()
            journal._inject(kind, 'after_commit')
    except BaseException as error:
        if committing:
            primary = JournalUncertain(f'release operation {operation} acknowledgement unknown')
            primary.__cause__ = error
        else:
            # This narrow protocol exposes the exact first error, including
            # SQLite entry/body faults; generic journal translation is unchanged.
            primary = error
    if retained is not None:
        errors = retained.cleanup()
        if errors:
            if primary is None:
                primary = JournalUncertain(f'release operation {operation} teardown unknown')
                primary.__cause__ = errors[0][1]
            primary.manifest_fence_owner = retained
    if primary is not None:
        raise primary
    return result
