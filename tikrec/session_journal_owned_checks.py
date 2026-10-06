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
    """Owned attempts remain unfinished task owners and retain all accounting pins."""
    rows = connection.execute("SELECT token FROM attempt_owners LIMIT 9").fetchall()
    require(len(rows) <= 8, "too many unfinished owned attempts")
    for selected in rows:
        row = owned_row(connection, selected["token"])
        identifier(row["owner"])
        sha256(row["seal_hash"])
        if row["marker_hash"] is not None:
            sha256(row["marker_hash"])
        task = connection.execute("SELECT * FROM tasks WHERE token=?", (row["token"],)).fetchone()
        session = connection.execute("SELECT * FROM sessions WHERE id=?", (row["session_id"],)).fetchone()
        require(task is not None and task["state"] == "running" and session["phase"] == "running"
                and session["seal_hash"] == row["seal_hash"], "owned attempt lost retained ownership")
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
        audit_publication(connection, row)
        from .session_journal_manifest_checks import audit_manifest
        audit_manifest(connection, row)
