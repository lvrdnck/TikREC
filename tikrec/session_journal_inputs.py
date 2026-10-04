"""Short read-only target projection; no filesystem reads or task claim."""

import json

from .session_journal_receipts import validate_operation_receipt, validate_session_receipt
from .session_journal_types import identifier


def sealed_input_projection(journal, session_id):
    """Atomically read one target, its retained ownership and current queue receipt."""
    identifier(session_id)
    def read(connection):
        journal._audit(connection)
        row = connection.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
        if row is None:
            return None
        validate_session_receipt(connection, row)
        result = dict(row)
        result["intent"] = json.loads(row["intent"])
        result["seal"] = None if row["seal"] is None else json.loads(row["seal"])
        for name, query in (
            ("task", "SELECT * FROM tasks WHERE session=?"),
            ("unit", "SELECT * FROM units WHERE session=?"),
            ("queue", "SELECT * FROM queue_entries WHERE session=? ORDER BY position DESC LIMIT 1")):
            value = connection.execute(query, (session_id,)).fetchone()
            result[name] = None if value is None else dict(value)
        result["artifacts"] = [dict(x) for x in connection.execute(
            "SELECT * FROM artifacts WHERE session=? ORDER BY kind LIMIT 2", (session_id,))]
        result["rooms"] = [x[0] for x in connection.execute(
            "SELECT room FROM rooms WHERE session=? LIMIT 2", (session_id,))]
        result["bound"] = connection.execute(
            "SELECT 1 FROM bindings WHERE session=?", (session_id,)).fetchone() is not None
        receipt = None if result["queue"] is None else connection.execute(
            "SELECT * FROM operations WHERE id=?", (result["queue"]["operation"],)).fetchone()
        if receipt is not None:
            validate_operation_receipt(connection, receipt)
        result["receipt"] = None if receipt is None else dict(receipt)
        return result
    return journal._read(read)
