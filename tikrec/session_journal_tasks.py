"""Guarded single-finalizer claims and exact-once task accounting settlement."""

import re
from dataclasses import asdict

from .session_journal_capture import intent_from_record
from .session_journal_types import (AttemptExitProof, JournalConflict, SettlementProof,
                                  encode, identifier, require)


def _guard(connection, session_id, revision, attempt, token):
    identifier(session_id)
    identifier(token)
    require(type(revision) is int and revision > 0 and type(attempt) is int and attempt > 0)
    row = connection.execute("SELECT * FROM tasks WHERE session=? AND revision=? "
                             "AND attempt=? AND token=?",
                             (session_id, revision, attempt, token)).fetchone()
    if row is None:
        raise JournalConflict("stale finalizer callback")
    if connection.execute("SELECT 1 FROM attempt_owners WHERE token=?", (token,)).fetchone():
        raise JournalConflict("owned attempt requires its child protocol; retain pins")
    return row


def claim(connection, token):
    """Share FIFO claiming without nesting journal transactions."""
    if connection.execute("SELECT 1 FROM tasks WHERE state='running' LIMIT 1").fetchone():
        return None
    row = connection.execute("SELECT * FROM tasks WHERE state='queued' "
             "ORDER BY queue_order LIMIT 1").fetchone()
    if row is None:
        return None
    connection.execute("INSERT INTO attempts VALUES (?,?,?,'running',NULL)",
               (token, row["session"], row["attempt"] + 1))
    connection.execute("UPDATE tasks SET state='running',revision=revision+1,"
               "attempt=attempt+1,token=?,error=NULL WHERE session=?",
               (token, row["session"]))
    connection.execute("UPDATE sessions SET phase='running',revision=revision+1 WHERE id=?",
               (row["session"],))
    return {"session_id": row["session"], "revision": row["revision"] + 1,
            "attempt": row["attempt"] + 1, "token": token}


def _exit(proof, session_id, token):
    require(type(proof) is AttemptExitProof and proof.session_id == session_id
            and proof.attempt_token == token, "attempt exit binding conflicts")


class TaskOperations:
    """Internal queue operations; no child process, publication or retry loop."""

    def claim_next(self, operation: str, attempt_token: str) -> dict | None:
        """Durably claim oldest queued task only when no other task is running."""
        identifier(attempt_token)
        def action(connection):
            return claim(connection, attempt_token)
        return self._mutate(operation, "claim_next", [attempt_token], action)

    def hold_attempt(self, operation: str, session_id: str, revision: int,
                     attempt: int, token: str, reason: str) -> dict:
        """Keep uncertain child work running/pinned, blocking a replacement finalizer."""
        require(type(reason) is str and re.fullmatch(r"[a-z_]{1,64}", reason) is not None)
        def action(connection):
            row = _guard(connection, session_id, revision, attempt, token)
            if row["state"] != "running":
                raise JournalConflict("attempt is not running")
            connection.execute("UPDATE tasks SET error=?,revision=revision+1 WHERE session=?",
                               (reason, session_id))
            return {"session_id": session_id, "revision": revision + 1,
                    "attempt": attempt, "token": token}
        return self._mutate(operation, "hold_attempt", [session_id, revision, attempt, token, reason], action)

    def fail_task(self, operation: str, session_id: str, revision: int,
                  attempt: int, token: str, proof: AttemptExitProof, reason: str) -> dict:
        """Record a proven failed child exit; retain its unit and all artifact/room pins."""
        _exit(proof, session_id, token)
        require(type(reason) is str and re.fullmatch(r"[a-z_]{1,64}", reason) is not None)
        def action(connection):
            row = _guard(connection, session_id, revision, attempt, token)
            if row["state"] != "running":
                raise JournalConflict("attempt is not running")
            connection.execute("UPDATE tasks SET state='failed',error=?,proof=?,revision=revision+1 "
                               "WHERE session=?", (reason, encode(asdict(proof)), session_id))
            connection.execute("UPDATE attempts SET state='failed',proof=? WHERE token=?",
                               (encode(asdict(proof)), token))
            connection.execute("UPDATE sessions SET phase='failed',revision=revision+1 WHERE id=?",
                               (session_id,))
            return {"session_id": session_id, "revision": revision + 1,
                    "attempt": attempt, "token": token}
        return self._mutate(operation, "fail_task",
                            [session_id, revision, attempt, token, asdict(proof), reason], action)

    def retry_failed(self, operation: str, session_id: str, revision: int,
                     attempt: int, token: str, proof: AttemptExitProof) -> dict:
        """Requeue at the durable FIFO tail without refunding the unit or moving on replay."""
        _exit(proof, session_id, token)
        def action(connection):
            row = _guard(connection, session_id, revision, attempt, token)
            if row["state"] != "failed" or row["proof"] != encode(asdict(proof)):
                raise JournalConflict("failed attempt proof conflicts")
            entry = connection.execute("INSERT INTO queue_entries(session,operation) VALUES (?,?)",
                                       (session_id, operation)).lastrowid
            self._inject("retry_failed", "after_queue_entry")
            connection.execute("UPDATE tasks SET state='queued',revision=revision+1,queue_order=? WHERE session=?",
                               (entry, session_id))
            self._inject("retry_failed", "after_task")
            connection.execute("UPDATE sessions SET phase='queued',revision=revision+1 WHERE id=?",
                               (session_id,))
            return {"session_id": session_id, "revision": revision + 1,
                    "attempt": attempt, "token": token, "queue_order": entry}
        return self._mutate(operation, "retry_failed",
                            [session_id, revision, attempt, token, asdict(proof)], action)

    def block_queued(self, operation: str, session_id: str, revision: int, reason: str) -> dict:
        """Pin unusable queued work without consuming a capture binding."""
        identifier(session_id)
        require(type(revision) is int and revision > 0)
        require(type(reason) is str and re.fullmatch(r"[a-z_]{1,64}", reason) is not None)
        def action(connection):
            row = connection.execute("SELECT * FROM tasks WHERE session=? AND revision=? "
                                     "AND state='queued'", (session_id, revision)).fetchone()
            if row is None:
                raise JournalConflict("stale queued task callback")
            connection.execute("UPDATE tasks SET state='blocked',error=?,revision=revision+1 "
                               "WHERE session=?", (reason, session_id))
            connection.execute("UPDATE sessions SET phase='blocked',revision=revision+1 WHERE id=?",
                               (session_id,))
            return {"session_id": session_id, "revision": revision + 1}
        return self._mutate(operation, "block_queued", [session_id, revision, reason], action)

    def settle_task(self, operation: str, session_id: str, revision: int,
                    attempt: int, token: str, proof: SettlementProof) -> dict:
        """Commit proven completion and release a task's unit/pins exactly once."""
        require(type(proof) is SettlementProof and proof.session_id == session_id
                and proof.attempt_token == token, "settlement attempt binding conflicts")
        def action(connection):
            row = _guard(connection, session_id, revision, attempt, token)
            if row["state"] != "running":
                raise JournalConflict("attempt is not running")
            session = connection.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
            intent = intent_from_record(session["intent"])
            require(proof.seal_hash == session["seal_hash"] and proof.output == intent.output,
                    "settlement artifact binding conflicts")
            connection.execute("UPDATE tasks SET state='completed',proof=?,revision=revision+1 "
                               "WHERE session=?", (encode(asdict(proof)), session_id))
            connection.execute("UPDATE attempts SET state='completed',proof=? WHERE token=?",
                               (encode(asdict(proof)), token))
            connection.execute("UPDATE sessions SET phase='completed',revision=revision+1 WHERE id=?",
                               (session_id,))
            self._inject("settle_task", "after_terminal")
            connection.execute("DELETE FROM units WHERE session=?", (session_id,))
            self._inject("settle_task", "after_unit_release")
            connection.execute("DELETE FROM artifacts WHERE session=?", (session_id,))
            connection.execute("DELETE FROM rooms WHERE session=?", (session_id,))
            self._inject("settle_task", "after_claim_release")
            return {"session_id": session_id, "revision": revision + 1,
                    "attempt": attempt, "token": token, "state": "completed"}
        return self._mutate(operation, "settle_task",
                            [session_id, revision, attempt, token, asdict(proof)], action)
