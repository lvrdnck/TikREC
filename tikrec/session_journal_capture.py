"""Atomic capture reservations, guarded admission and sealed handoff H."""

import json
from dataclasses import asdict

from .session_journal_types import (ArtifactIdentity, ClosureSeal, JournalConflict,
                                  ReservationReleaseProof, SessionIntent, digest, encode,
                                  identifier, require, room)


def intent_from_record(record: str) -> SessionIntent:
    """Revalidate stored immutable intent without reading any media or filesystem."""
    values = json.loads(record)
    for key in ("root", "output", "parts"):
        identity = values[key]
        values[key] = ArtifactIdentity(identity["volume"], tuple(identity["components"]))
    return SessionIntent(**values)


def guard_capture(connection, session_id, generation, revision):
    """Match UUID, generation and revision; never target a replacement slot owner."""
    identifier(session_id)
    require(type(generation) is int and generation > 0
            and type(revision) is int and revision > 0)
    row = connection.execute("SELECT s.*,b.slot FROM sessions s JOIN bindings b "
                             "ON b.session=s.id WHERE s.id=? AND b.generation=? "
                             "AND s.revision=?", (session_id, generation, revision)).fetchone()
    if row is None:
        raise JournalConflict("stale capture callback")
    return row


def _result(row, revision=None):
    return {"session_id": row["id"], "slot": row["origin_slot"],
            "generation": row["generation"],
            "revision": row["revision"] if revision is None else revision}


def _ownership(connection, intent, proven_room, *, excluding=None):
    owners = connection.execute("SELECT s.*,u.kind FROM sessions s JOIN units u "
                                "ON u.session=s.id WHERE s.id IS NOT ? LIMIT 9",
                                (excluding,)).fetchall()
    for owner in owners:
        old_room = owner["room"] or owner["expected_room"]
        if old_room is not None and old_room == proven_room:
            raise JournalConflict("public room already owned")
        if owner["creator"] == intent.creator:
            # A free slot cannot bypass a current page owner or an unknown old room.
            if owner["kind"] == "capture" or old_room is None or proven_room is None:
                raise JournalConflict("public page ownership cannot be separated")
    rows = connection.execute("SELECT * FROM artifacts WHERE session IS NOT ? LIMIT 17",
                              (excluding,)).fetchall()
    for row in rows:
        value = json.loads(row["identity"])
        old = ArtifactIdentity(value["volume"], tuple(value["components"]))
        if old.overlaps(intent.output) or old.overlaps(intent.parts):
            raise JournalConflict("artifact identity or subtree already owned")


class CaptureOperations:
    """Internal transitions only; this mixin does not start or stop a LIVE."""

    def reserve(self, operation: str, intent: SessionIntent, *, slot: int | None = None) -> dict:
        """Atomically accept immutable intent, paths, receipt, binding and one work unit."""
        require(type(intent) is SessionIntent)
        require(slot is None or type(slot) is int and slot in {1, 2})
        values = asdict(intent)
        def action(connection):
            if intent.automatic_claim is not None:
                receipt = connection.execute("SELECT * FROM automatic_receipts WHERE claim=?",
                                             (intent.automatic_claim,)).fetchone()
                if receipt is not None:
                    if receipt["intent_hash"] != digest(values):
                        raise JournalConflict("automatic claim identity conflicts")
                    previous = connection.execute("SELECT * FROM sessions WHERE id=?",
                                                  (receipt["session"],)).fetchone()
                    return _result(previous, 1)
            if connection.execute("SELECT 1 FROM sessions WHERE id=?", (intent.session_id,)).fetchone():
                raise JournalConflict("session already accepted")
            _ownership(connection, intent, intent.expected_room)
            if connection.execute("SELECT count(*) FROM units").fetchone()[0] >= 8:
                raise JournalConflict("outstanding work limit")
            binding = connection.execute("SELECT * FROM bindings WHERE session IS NULL "
                                         "AND (? IS NULL OR slot=?) ORDER BY slot LIMIT 1",
                                         (slot, slot)).fetchone()
            if binding is None:
                raise JournalConflict("capture capacity unavailable")
            generation = binding["generation"] + 1
            connection.execute("INSERT INTO sessions(id,intent,creator,expected_room,origin_slot,"
                               "generation,phase,revision) VALUES (?,?,?,?,?,?,'reserved',1)",
                               (intent.session_id, encode(values), intent.creator,
                                intent.expected_room, binding["slot"], generation))
            self._inject("reserve", "after_session")
            connection.execute("UPDATE bindings SET session=?,generation=? WHERE slot=?",
                               (intent.session_id, generation, binding["slot"]))
            self._inject("reserve", "after_binding")
            connection.execute("INSERT INTO units VALUES (?,'capture')", (intent.session_id,))
            self._inject("reserve", "after_unit")
            for kind in ("output", "parts"):
                connection.execute("INSERT INTO artifacts VALUES (?,?,?)",
                                   (intent.session_id, kind, encode(values[kind])))
            if intent.expected_room is not None:
                connection.execute("INSERT INTO rooms VALUES (?,?)",
                                   (intent.expected_room, intent.session_id))
            self._inject("reserve", "after_claims")
            if intent.automatic_claim is not None:
                connection.execute("INSERT INTO automatic_receipts VALUES (?,?,?)",
                                   (intent.automatic_claim, intent.session_id, digest(values)))
            self._inject("reserve", "after_receipt")
            return {"session_id": intent.session_id, "slot": binding["slot"],
                    "generation": generation, "revision": 1}
        return self._mutate(operation, "reserve", {"intent": values, "slot": slot}, action)

    def admit(self, operation: str, session_id: str, generation: int,
              revision: int, proven_room: str) -> dict:
        """Record caller-proven source room before the reserved capture may write."""
        room(proven_room)
        require(proven_room is not None)
        def action(connection):
            row = guard_capture(connection, session_id, generation, revision)
            intent = intent_from_record(row["intent"])
            if row["phase"] != "reserved" or (intent.expected_room is not None
                                               and intent.expected_room != proven_room):
                raise JournalConflict("reservation or room proof conflicts")
            _ownership(connection, intent, proven_room, excluding=session_id)
            connection.execute("INSERT OR IGNORE INTO rooms VALUES (?,?)", (proven_room, session_id))
            connection.execute("UPDATE sessions SET room=?,phase='capturing',revision=revision+1 "
                               "WHERE id=?", (proven_room, session_id))
            return _result(row, revision + 1)
        return self._mutate(operation, "admit", [session_id, generation, revision, proven_room], action)

    def capture_intent(self, operation: str, session_id: str, generation: int,
                       revision: int, *, closing: bool = False, stop: bool = False,
                       recovery: str | None = None) -> dict:
        """Guard stop/recovery/closing intent; stop intent can never be cleared."""
        require(type(closing) is bool and type(stop) is bool)
        require(recovery in {None, "process_restart", "network_outage", "network_recovered",
                             "room_ended", "user_stop", "identity_unavailable", "ambiguous_state"})
        def action(connection):
            row = guard_capture(connection, session_id, generation, revision)
            phase = "closing" if closing else row["phase"]
            recovery_reason = recovery if recovery is not None else row["recovery"]
            connection.execute("UPDATE sessions SET phase=?,stop=?,recovery=?,revision=revision+1 "
                               "WHERE id=?", (phase, bool(stop or row["stop"]), recovery_reason, session_id))
            return _result(row, revision + 1)
        return self._mutate(operation, "capture_intent",
                            [session_id, generation, revision, closing, stop, recovery], action)

    def handoff(self, operation: str, session_id: str, generation: int,
                revision: int, seal: ClosureSeal) -> dict:
        """Atomically seal a task and transfer its existing unit before slot reuse."""
        require(type(seal) is ClosureSeal)
        values = asdict(seal)
        def action(connection):
            row = guard_capture(connection, session_id, generation, revision)
            intent = intent_from_record(row["intent"])
            require(row["phase"] == "closing" and row["room"] is not None
                    and seal.session_id == session_id and seal.generation == generation
                    and seal.room_id == row["room"] and seal.raw_copy == intent.raw_copy
                    and seal.ended_at >= intent.started_at, "seal binding conflicts")
            for artifact in seal.artifacts:
                require(intent.parts.contains(artifact.identity)
                        and artifact.identity != intent.parts, "seal outside owned parts")
            connection.execute("UPDATE sessions SET phase='queued',revision=revision+1,"
                               "seal=?,seal_hash=? WHERE id=?",
                               (encode(values), digest(values), session_id))
            self._inject("handoff", "after_seal")
            connection.execute("INSERT INTO tasks(session,state,revision) VALUES (?,'queued',1)",
                               (session_id,))
            self._inject("handoff", "after_task")
            connection.execute("UPDATE units SET kind='task' WHERE session=?", (session_id,))
            self._inject("handoff", "after_transfer")
            connection.execute("UPDATE bindings SET session=NULL WHERE session=?", (session_id,))
            self._inject("handoff", "after_release")
            # Artifact and old-room rows are deliberately untouched by handoff H.
            return {**_result(row, revision + 1), "task_revision": 1, "seal_hash": digest(values)}
        return self._mutate(operation, "handoff", [session_id, generation, revision, values], action)

    def settle_reservation(self, operation: str, session_id: str, generation: int,
                           revision: int, no_writer_proof: ReservationReleaseProof) -> dict:
        """Release an unadmitted reservation only with caller-proven writer absence.

        This isolated operation cannot settle a capture that has admitted a writer;
        that requires later native closure/no-assembly evidence integration.
        """
        require(type(no_writer_proof) is ReservationReleaseProof
                and no_writer_proof.session_id == session_id
                and no_writer_proof.generation == generation, "reservation proof binding conflicts")
        def action(connection):
            row = guard_capture(connection, session_id, generation, revision)
            if row["phase"] != "reserved":
                raise JournalConflict("writer closure required for admitted capture")
            connection.execute("UPDATE sessions SET phase='no_assembly',revision=revision+1 WHERE id=?",
                               (session_id,))
            connection.execute("DELETE FROM units WHERE session=?", (session_id,))
            connection.execute("DELETE FROM artifacts WHERE session=?", (session_id,))
            connection.execute("DELETE FROM rooms WHERE session=?", (session_id,))
            connection.execute("UPDATE bindings SET session=NULL WHERE session=?", (session_id,))
            return _result(row, revision + 1)
        return self._mutate(operation, "settle_reservation",
                            [session_id, generation, revision, asdict(no_writer_proof)], action)
