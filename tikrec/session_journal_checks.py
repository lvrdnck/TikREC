"""Bounded cross-table ownership/accounting validation for the isolated journal."""

from .session_journal_capture import intent_from_record
from dataclasses import asdict

from .session_journal_types import closure_from_record, digest, encode, require, room


def audit(connection) -> None:
    """Reject missing/contradictory outstanding claims without discarding history."""
    # Outstanding rows are bounded by eight; history need not be returned or scanned.
    units = connection.execute("SELECT * FROM units LIMIT 9").fetchall()
    bindings = connection.execute("SELECT * FROM bindings ORDER BY slot LIMIT 3").fetchall()
    require(len(units) <= 8 and [x["slot"] for x in bindings] == [1, 2],
            "invalid journal accounting")
    for unit in units:
        row = connection.execute("SELECT * FROM sessions WHERE id=?", (unit["session"],)).fetchone()
        require(row is not None, "missing session ownership")
        intent = intent_from_record(row["intent"])
        require(intent.session_id == row["id"] and intent.creator == row["creator"]
                and intent.expected_room == row["expected_room"], "invalid immutable ownership")
        room(row["room"])
        require(row["room"] is None or intent.expected_room in {None, row["room"]},
                "conflicting accepted room")
        if row["seal"] is not None:
            seal = closure_from_record(row["seal"])
            require(digest(asdict(seal)) == row["seal_hash"] and seal.session_id == row["id"]
                    and seal.generation == row["generation"] and seal.room_id == row["room"]
                    and seal.raw_copy == intent.raw_copy and seal.ended_at >= intent.started_at
                    and all(intent.parts.contains(a.identity) and a.identity != intent.parts
                            for a in seal.artifacts), "invalid closure binding")
        claims = connection.execute("SELECT kind,identity FROM artifacts WHERE session=? LIMIT 3",
                                    (row["id"],)).fetchall()
        require(dict(claims) == {"output": encode(asdict(intent.output)),
                                "parts": encode(asdict(intent.parts))}, "artifact binding conflicts")
    for unit in units:
        sid = unit["session"]
        session = connection.execute("SELECT * FROM sessions WHERE id=?", (sid,)).fetchone()
        binding = connection.execute("SELECT * FROM bindings WHERE session=?", (sid,)).fetchone()
        task = connection.execute("SELECT * FROM tasks WHERE session=?", (sid,)).fetchone()
        if unit["kind"] == "capture":
            require(binding is not None and task is None
                    and session["phase"] in {"reserved", "capturing", "closing"}
                    and binding["generation"] == session["generation"]
                    and binding["slot"] == session["origin_slot"], "invalid capture ownership")
        else:
            require(binding is None and task is not None and task["state"] != "completed"
                    and session["phase"] == task["state"] and session["seal"] is not None,
                    "invalid task ownership")
            if task["token"] is not None:
                attempt = connection.execute("SELECT * FROM attempts WHERE token=?",
                                             (task["token"],)).fetchone()
                expected = "failed" if task["state"] in {"queued", "blocked"} else task["state"]
                require(attempt is not None and attempt["session"] == sid
                        and attempt["number"] == task["attempt"]
                        and attempt["state"] == expected, "invalid attempt ownership")
        require(connection.execute("SELECT count(*) FROM artifacts WHERE session=?", (sid,))
                .fetchone()[0] == 2, "missing artifact ownership")
        claimed = connection.execute("SELECT room FROM rooms WHERE session=? LIMIT 2", (sid,)).fetchall()
        expected_room = session["room"] or session["expected_room"]
        require([x[0] for x in claimed] == ([] if expected_room is None else [expected_room]),
                "missing or conflicting room ownership")
    require(connection.execute("SELECT count(*) FROM bindings b LEFT JOIN units u "
                               "ON b.session=u.session WHERE b.session IS NOT NULL "
                               "AND (u.kind IS NULL OR u.kind!='capture')").fetchone()[0] == 0,
            "unaccounted capture binding")
    require(connection.execute("SELECT count(*) FROM tasks t LEFT JOIN units u "
                               "ON t.session=u.session WHERE t.state!='completed' "
                               "AND (u.kind IS NULL OR u.kind!='task')").fetchone()[0] == 0,
            "unaccounted finalization task")
    require(connection.execute("SELECT 1 FROM sessions s LEFT JOIN units u ON u.session=s.id "
                               "WHERE s.phase NOT IN ('completed','no_assembly') AND u.session IS NULL "
                               "LIMIT 1").fetchone() is None, "unaccounted session")
    require(connection.execute("SELECT 1 FROM artifacts a LEFT JOIN units u ON u.session=a.session "
                               "WHERE u.session IS NULL LIMIT 1").fetchone() is None,
            "unaccounted artifact ownership")
    require(connection.execute("SELECT 1 FROM rooms r LEFT JOIN units u ON u.session=r.session "
                               "WHERE u.session IS NULL LIMIT 1").fetchone() is None,
            "unaccounted room ownership")
    require(connection.execute("SELECT 1 FROM attempts a LEFT JOIN tasks t ON t.token=a.token "
                               "WHERE a.state='running' AND (t.state IS NULL OR t.state!='running') "
                               "LIMIT 1").fetchone() is None, "unaccounted running attempt")
