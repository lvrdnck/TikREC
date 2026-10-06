"""Bounded current owned-attempt inspection; receipts never authorize adoption."""

import json
from contextlib import contextmanager

from .session_journal_inputs import input_projection
from .session_journal_types import identifier, require


def owned_row(connection, token):
    """Return the current child and owner, without scanning historical launches."""
    row = connection.execute("SELECT * FROM attempt_owners WHERE token=?", (token,)).fetchone()
    if row is None:
        return None
    result = dict(row)
    attempt = connection.execute("SELECT * FROM attempts WHERE token=?", (token,)).fetchone()
    result["session_id"], result["attempt"] = attempt["session"], attempt["number"]
    child = connection.execute("SELECT * FROM child_launches WHERE token=? AND sequence=?",
                               (token, row["sequence"])).fetchone()
    result["child"] = None if child is None else dict(child)
    if child is not None:
        for field in ("intent", "identity", "exit", "diagnostics"):
            result["child"][field] = None if child[field] is None else json.loads(child[field])
    scratch = connection.execute("SELECT * FROM scratch_owners WHERE token=?", (token,)).fetchone()
    result["scratch"] = None if scratch is None else dict(scratch)
    if result["scratch"] is not None:
        result["scratch"]["intent"] = json.loads(scratch["intent"])
        result["scratch"]["workspace_identity"] = (None if scratch["workspace_identity"] is None
                                                       else json.loads(scratch["workspace_identity"]))
        result["scratch"]["artifacts"] = [dict(x) for x in connection.execute(
            "SELECT * FROM scratch_artifacts WHERE token=? ORDER BY name LIMIT 32", (token,))]
        candidate = connection.execute("SELECT * FROM scratch_candidates WHERE token=?", (token,)).fetchone()
        result["scratch"]["candidate"] = None if candidate is None else dict(candidate)
        if result["scratch"]["candidate"] is not None:
            for field in ("identity", "execution"):
                result["scratch"]["candidate"][field] = json.loads(candidate[field])
        result["scratch"]["hold_reason"] = (None if scratch["hold_reason"] is None
                                             else json.loads(scratch["hold_reason"]))
    return result


def owner_guard(connection, token, owner, revision, *, launch=False, cleanup=False):
    """Fence every mutation/resume against exact current local owner and revision."""
    identifier(token)
    identifier(owner)
    require(type(revision) is int and revision > 0)
    row = owned_row(connection, token)
    require(row is not None and row["owner"] == owner and row["revision"] == revision,
            "stale owned attempt")
    task = connection.execute("SELECT * FROM tasks WHERE token=?", (token,)).fetchone()
    require(task is not None and task["state"] == "running" and task["attempt"] == row["attempt"],
            "owned attempt lost task ownership")
    if not cleanup:
        require(connection.execute('SELECT 1 FROM release_preparations WHERE token=?', (token,)).fetchone()
                is None, 'attempt permits only prepared cleanup/accounting')
    if launch:
        require(row["state"] == "held" and row["marker_hash"] is not None,
                "revoked or unprotected attempt cannot launch")
    return row


def audit_history(connection, token):
    """Check only the addressed terminal owner; active owners already have bounded audit."""
    task = connection.execute("SELECT state FROM tasks WHERE token=?", (token,)).fetchone()
    if task is not None and task['state'] == 'completed':
        from .session_journal_owned_checks import audit_owner
        audit_owner(connection, token, historical=True)


class OwnedViews:
    """Read-only explicit inspection and the short final resume fence."""

    def owned_attempt(self, token):
        """Read interrupted facts without inferring exit or granting local ownership."""
        identifier(token)
        def read(connection):
            self._audit(connection)
            task = connection.execute('SELECT state FROM tasks WHERE token=?', (token,)).fetchone()
            if task is not None:
                from .session_journal_owned_checks import audit_owner
                audit_owner(connection, token, historical=task['state'] == 'completed')
            return owned_row(connection, token)
        return self._read(read)

    def claimed_input(self, token):
        """Project current attempt ownership and original H receipt separately."""
        identifier(token)
        def read(connection):
            owned = owned_row(connection, token)
            require(owned is not None, "missing owned attempt")
            result = input_projection(self, connection, owned["session_id"])
            result["owned"] = owned
            receipt = connection.execute("SELECT * FROM operations WHERE id=?",
                                         (owned["h_operation"],)).fetchone()
            queue = connection.execute("SELECT * FROM queue_entries WHERE operation=?",
                                       (owned["h_operation"],)).fetchone()
            result["h_receipt"], result["h_queue"] = dict(receipt), dict(queue)
            return result
        return self._read(read)

    def child_history(self, token, *, after=0, limit=50):
        """Page permanent child identities without interpreting history as permission."""
        identifier(token)
        require(type(after) is int and after >= 0 and type(limit) is int and 1 <= limit <= 100)
        return self._read(lambda connection: [dict(row) for row in connection.execute(
            "SELECT * FROM child_launches WHERE token=? AND sequence>? ORDER BY sequence LIMIT ?",
            (token, after, limit))])

    @contextmanager
    def resume_fence(self, token, owner, revision, launch, identity):
        """Serialize immediate native resume against durable revocation commit.

        Only exact identity verification and ResumeThread belong inside this short
        read transaction. Never scan inputs, wait, stream or run caller hooks here.
        DELETE-mode read ownership prevents a concurrent revocation COMMIT.
        """
        connection = self._connect()
        try:
            connection.execute("BEGIN")
            row = owner_guard(connection, token, owner, revision, launch=True)
            require(row["child"] is not None and row["child"]["id"] == launch
                    and row["child"]["identity"] == identity and row["child"]["exit"] is None,
                    "stale child resume authorization")
            yield
        finally:
            connection.close()
