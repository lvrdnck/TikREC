"""Validate keyed automatic provenance without scanning completed history."""

import json
from dataclasses import asdict

from .session_journal_types import digest, identifier, intent_from_record, require


def validate_session_receipt(connection, session, intent=None):
    """Bind immutable claim/session/intent; a receipt is not writer permission."""
    intent = intent or intent_from_record(session["intent"])
    require(intent.session_id == session["id"] and intent.creator == session["creator"]
            and intent.expected_room == session["expected_room"]
            and intent.automatic_claim == session["automatic_claim"], "invalid immutable receipt binding")
    receipt = connection.execute("SELECT * FROM automatic_receipts WHERE session=?",
                                 (session["id"],)).fetchone()
    if intent.automatic_claim is None:
        require(receipt is None, "unexpected automatic provenance for manual intent")
    else:
        require(receipt is not None and receipt["claim"] == intent.automatic_claim
                and receipt["session"] == intent.session_id
                and receipt["intent_hash"] == digest(asdict(intent)), "invalid automatic receipt binding")
    return receipt


def lookup_receipt(connection, claim_id: str):
    """Validate the addressed live or historical claim, including a missing receipt."""
    receipt = connection.execute("SELECT * FROM automatic_receipts WHERE claim=?", (claim_id,)).fetchone()
    # This unique indexed session column proves whether a missing claim was accepted.
    session = connection.execute("SELECT * FROM sessions WHERE automatic_claim=?", (claim_id,)).fetchone()
    if session is None:
        require(receipt is None, "receipt lacks matching accepted claim")
        return None
    validated = validate_session_receipt(connection, session)
    require(receipt is not None and dict(receipt) == dict(validated), "receipt session binding conflicts")
    return dict(validated)


def validate_operation_receipt(connection, receipt):
    """Revalidate the addressed historical session while preserving operation replay."""
    result = json.loads(receipt["result"])
    if isinstance(result, dict) and "session_id" in result:
        identifier(result["session_id"])
        session = connection.execute("SELECT * FROM sessions WHERE id=?", (result["session_id"],)).fetchone()
        require(session is not None, "operation receipt lacks accepted session")
        validate_session_receipt(connection, session)
        if 'token' in result and 'owner' in result:
            from .session_journal_owned_checks import audit_owner
            task = connection.execute('SELECT state FROM tasks WHERE token=?', (result['token'],)).fetchone()
            require(task is not None, 'owned receipt lacks task history')
            audit_owner(connection, result['token'], historical=task['state'] == 'completed')
    return result
