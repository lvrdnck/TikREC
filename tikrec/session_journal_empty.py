"""Proved admitted empty capture retains evidence claims without an assembly task."""

from dataclasses import asdict

from .session_journal_capture import guard_capture, _result
from .session_journal_types import ClosureSeal, digest, encode, intent_from_record, require


class EmptyCaptureOperations:
    """Release capture capacity while keeping admitted empty evidence pinned/counted."""

    def settle_empty_capture(self, operation, session_id, generation, revision, seal):
        """Commit native-proved zero-media closure; failed/ambiguous capture cannot use it."""
        require(type(seal) is ClosureSeal and seal.disposition == "empty")
        values = asdict(seal)
        def action(connection):
            row = guard_capture(connection, session_id, generation, revision)
            intent = intent_from_record(row["intent"])
            require(row["phase"] == "closing" and row["room"] is not None
                    and row["recovery"] not in {"ambiguous_state", "network_outage", "process_restart"}
                    and seal.session_id == session_id and seal.generation == generation
                    and seal.room_id == row["room"] and seal.raw_copy == intent.raw_copy
                    and seal.ended_at >= intent.started_at
                    and all(intent.parts.contains(a.identity) and a.identity != intent.parts
                            for a in seal.artifacts), "empty closure binding conflicts")
            connection.execute("UPDATE sessions SET phase='no_assembly',revision=revision+1,"
                               "seal=?,seal_hash=? WHERE id=?", (encode(values), digest(values), session_id))
            self._inject("settle_empty_capture", "after_seal")
            connection.execute("UPDATE units SET kind='evidence' WHERE session=?", (session_id,))
            self._inject("settle_empty_capture", "after_transfer")
            connection.execute("UPDATE bindings SET session=NULL WHERE session=?", (session_id,))
            self._inject("settle_empty_capture", "after_release")
            # Empty capture still owns its artifacts, room and bounded retained unit.
            return {**_result(row, revision + 1), "seal_hash": digest(values)}
        return self._mutate(operation, "settle_empty_capture",
                            [session_id, generation, revision, values], action)
