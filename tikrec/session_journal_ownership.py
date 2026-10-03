"""One bounded ownership rule shared by admission and stored-state auditing."""

from .session_journal_types import JournalConflict, SessionIntent, intent_from_record


def ownership_conflict(left: SessionIntent, left_room: str | None, left_kind: str,
                       right: SessionIntent, right_room: str | None, right_kind: str) -> str | None:
    """Compare validated claims; native alias evidence must still come from an adapter."""
    if left_room is not None and left_room == right_room:
        return "public room already owned"
    if left.creator == right.creator:
        # Only separated known rooms with at least one closed capture permit reuse.
        if left_kind == right_kind == "capture" or left_room is None or right_room is None:
            return "public page ownership cannot be separated"
    for left_path in (left.output, left.parts):
        for right_path in (right.output, right.parts):
            if left_path.overlaps(right_path):
                return "artifact identity or subtree already owned"
    return None


def check_admission(connection, intent: SessionIntent, proven_room: str | None,
                    *, excluding: str | None = None) -> None:
    """Refuse a new capture against at most eight authoritative outstanding owners."""
    owners = connection.execute("SELECT s.*,u.kind FROM units u JOIN sessions s ON s.id=u.session "
                                "WHERE s.id IS NOT ? LIMIT 9", (excluding,)).fetchall()
    for owner in owners:
        conflict = ownership_conflict(intent, proven_room, "capture", intent_from_record(owner["intent"]),
                                      owner["room"] or owner["expected_room"], owner["kind"])
        if conflict is not None:
            raise JournalConflict(conflict)
