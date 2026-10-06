"""Bounded current durable child ownership checks; no historical launch permission."""

import json

from .session_journal_owned_view import owned_row
from .session_journal_types import digest, identifier, require, sha256


def receipt(connection, operation, kind):
    """Require a committed receipt of the declared phase."""
    row = connection.execute("SELECT * FROM operations WHERE id=?", (operation,)).fetchone()
    require(row is not None and row["kind"] == kind, "owned record lacks operation receipt")
    return row, json.loads(row["result"])


def audit_child(connection, row, child):
    """Check one current or immediate predecessor; history stays paged."""
    intent = json.loads(child["intent"])
    identifier(child["id"])
    require(("access" not in intent and "outputs" not in intent)
            or intent.get("access") == "write" and type(intent.get("outputs")) is list
            or intent.get("access") == "candidate_validation" and "validation_operation" in intent,
            "invalid child filesystem authority")
    require(intent["seal_hash"] == row["seal_hash"] and intent["marker_hash"] == row["marker_hash"],
            "child seal/marker conflicts")
    op, result = receipt(connection, child["intent_operation"], "launch_intent")
    require(result["launch"] == child["id"] and result["sequence"] == child["sequence"]
            and result["token"] == row["token"] and result["owner"] == row["owner"]
            and op["arguments_hash"] == digest([row["token"], row["owner"],
                result["previous_revision"], child["id"], intent]), "child intent receipt conflicts")
    for field in ("identity", "exit", "diagnostics", "cleanup"):
        value = child[field]
        if value in (None, 0):
            continue
        value = value if field == "cleanup" else json.loads(value)
        op, result = receipt(connection, child[field + "_operation"], "child_" + field)
        require(result["launch"] == child["id"] and result["field"] == field
                and result["token"] == row["token"] and result["owner"] == row["owner"]
                and op["arguments_hash"] == digest([row["token"], row["owner"],
                    result["previous_revision"], child["id"], value]), "child phase receipt conflicts")
    if child["exit"] is not None:
        value = json.loads(child["exit"])
        identity = None if child["identity"] is None else json.loads(child["identity"])
        require(value["state"] == "not_created" and identity is None or
                value["state"] == "confirmed_exited" and value["active"] == 0
                and value["identity"] is not None and (identity is None or identity == value["identity"]),
                "invalid durable whole-job exit")


def audit_owned(connection):
    """Audit at most eight outstanding owners using the bounded active unit index."""
    rows = connection.execute("SELECT o.token FROM units u JOIN tasks t ON t.session=u.session "
        "JOIN attempt_owners o ON o.token=t.token WHERE u.kind='task' LIMIT 9").fetchall()
    require(len(rows) <= 8, "too many unfinished owned attempts")
    for selected in rows:
        audit_owner(connection, selected['token'])


def audit_owner(connection, token, *, historical=False):
    """Validate one addressed owner; completed history requires exact release receipts."""
    row = owned_row(connection, token)
    identifier(row["owner"])
    sha256(row["seal_hash"])
    if row["marker_hash"] is not None:
        sha256(row["marker_hash"])
    task = connection.execute("SELECT * FROM tasks WHERE token=?", (row["token"],)).fetchone()
    session = connection.execute("SELECT * FROM sessions WHERE id=?", (row["session_id"],)).fetchone()
    require(task is not None and session is not None and session["seal_hash"] == row["seal_hash"],
            "owned attempt lost immutable session")
    from .session_journal_receipts import validate_session_receipt
    validate_session_receipt(connection, session)
    require(session['seal'] is not None and digest(json.loads(session['seal'])) == row['seal_hash'],
            'owned history seal conflicts')
    if historical:
        terminal = connection.execute('SELECT evidence FROM release_results WHERE token=?', (token,)).fetchone()
        attempt = connection.execute('SELECT state,proof FROM attempts WHERE token=?', (token,)).fetchone()
        require(terminal is not None and task['state'] == session['phase'] == attempt['state'] == 'completed'
                and task['proof'] == attempt['proof'] == terminal['evidence']
                and connection.execute('SELECT 1 FROM units WHERE session=?', (row['session_id'],)).fetchone() is None
                and connection.execute('SELECT 1 FROM artifacts WHERE session=?', (row['session_id'],)).fetchone() is None
                and connection.execute('SELECT 1 FROM rooms WHERE session=?', (row['session_id'],)).fetchone() is None,
                'released history has active or contradictory ownership')
    else:
        require(task['state'] == session['phase'] == 'running', 'owned attempt lost retained ownership')
    op, result = receipt(connection, row["claim_operation"], "claim_owned")
    require(result["token"] == row["token"] and result["owner"] == row["owner"]
            and result["session_id"] == row["session_id"]
            and op["arguments_hash"] == digest([row["token"], row["owner"]]),
            "owned claim receipt conflicts")
    _, h = receipt(connection, row["h_operation"], "handoff")
    require(h["revision"] == row["h_revision"] and h["session_id"] == row["session_id"]
            and h["seal_hash"] == row["seal_hash"], "original H conflicts")
    latest = connection.execute("SELECT result FROM operations WHERE id=?", (row["last_operation"],)).fetchone()
    require(latest is not None and json.loads(latest[0])["revision"] == row["revision"],
            "owned revision lacks receipt")
    latest_result = json.loads(latest[0])
    require(latest_result["token"] == row["token"] and latest_result["owner"] == row["owner"]
            and latest_result["session_id"] == row["session_id"], "owned current receipt conflicts")
    children = connection.execute("SELECT * FROM child_launches WHERE token=? AND sequence>=? "
                                  "ORDER BY sequence LIMIT 3", (row["token"], max(1, row["sequence"] - 1))).fetchall()
    require(len(children) == min(2, row["sequence"]) and
            (not children or children[-1]["sequence"] == row["sequence"]), "child sequence conflicts")
    for child in children:
        audit_child(connection, row, child)
    if len(children) == 2:
        prior, current = children
        require(json.loads(current["intent"])["predecessor"] == prior["id"]
                and prior["exit"] is not None and prior["cleanup"] == 1
                and json.loads(prior["diagnostics"])["complete"], "premature successor child")
    from .session_journal_scratch_checks import audit_scratch
    audit_scratch(connection, row)
    from .session_journal_validation_checks import audit_validation
    audit_validation(connection, row)

    from .session_journal_publication_checks import audit_publication
    audit_publication(connection, row, historical=historical)
    from .session_journal_manifest_checks import audit_manifest
    audit_manifest(connection, row)
    from .session_journal_settlement_checks import audit_settlement
    audit_settlement(connection, row, historical=historical)
