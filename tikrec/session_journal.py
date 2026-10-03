"""Isolated internal durable session journal, deliberately unused by the service."""

import json

from .session_journal_capture import CaptureOperations
from .session_journal_store import JournalStore
from .session_journal_tasks import TaskOperations
from .session_journal_types import identifier, require


class SessionJournal(CaptureOperations, TaskOperations, JournalStore):
    """Explicit-path authority with two capture bindings and one finalizer claim."""

    def session(self, session_id: str) -> dict | None:
        """Read one independent session, including its immutable evidence and task."""
        identifier(session_id)
        def read(connection):
            row = connection.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
            if row is None:
                return None
            result = dict(row)
            result["intent"] = json.loads(result["intent"])
            result["seal"] = None if row["seal"] is None else json.loads(row["seal"])
            task = connection.execute("SELECT * FROM tasks WHERE session=?", (session_id,)).fetchone()
            result["task"] = None if task is None else dict(task)
            result["artifacts"] = [dict(x) for x in connection.execute(
                "SELECT * FROM artifacts WHERE session=? ORDER BY kind LIMIT 2", (session_id,))]
            result["rooms"] = [x[0] for x in connection.execute(
                "SELECT room FROM rooms WHERE session=? LIMIT 2", (session_id,))]
            return result
        return self._read(read)

    def automatic_receipt(self, claim_id: str) -> dict | None:
        """Find permanent accepted-start provenance even after capture slot reuse."""
        identifier(claim_id)
        def read(connection):
            row = connection.execute("SELECT * FROM automatic_receipts WHERE claim=?", (claim_id,)).fetchone()
            return None if row is None else dict(row)
        return self._read(read)

    def status(self) -> dict:
        """Return bounded internal counts/bindings, separately from MP4 completion."""
        def read(connection):
            self._audit(connection)
            return {"bindings": [dict(x) for x in connection.execute(
                        "SELECT * FROM bindings ORDER BY slot LIMIT 2")],
                    "units": [dict(x) for x in connection.execute(
                        "SELECT * FROM units ORDER BY session LIMIT 8")],
                    "tasks": [dict(x) for x in connection.execute(
                        "SELECT * FROM tasks WHERE state!='completed' ORDER BY session LIMIT 8")],
                    "limit": 8}
        return self._read(read)

    def history(self, *, after: int = 0, limit: int = 50) -> list[dict]:
        """Page metadata by immutable sequence without exposing unbounded history."""
        require(type(after) is int and after >= 0 and type(limit) is int and 1 <= limit <= 100)
        return self._read(lambda connection: [dict(x) for x in connection.execute(
            "SELECT seq,id,creator,room,phase,revision,origin_slot,generation FROM sessions "
            "WHERE seq>? ORDER BY seq LIMIT ?", (after, limit))])
