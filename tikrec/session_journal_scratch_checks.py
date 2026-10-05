"""Audit durable scratch and candidate history without granting process adoption."""

import json

from .session_journal_types import digest, require, sha256


def _operation(connection, operation, kind, arguments):
    """Require one immutable operation receipt to match its durable record."""
    row = connection.execute("SELECT * FROM operations WHERE id=?", (operation,)).fetchone()
    require(row is not None and row["kind"] == kind
            and row["arguments_hash"] == digest(arguments), "scratch operation receipt conflicts")
    return json.loads(row["result"])


def audit_scratch(connection, owner):
    """Verify bounded reservation, native bindings and unpublished outcome facts."""
    token = owner["token"]
    scratch = connection.execute("SELECT * FROM scratch_owners WHERE token=?", (token,)).fetchone()
    if scratch is None:
        return
    require(scratch["owner"] == owner["owner"] and scratch["session"] == owner["session_id"])
    intent = json.loads(scratch["intent"])
    metadata = connection.execute("SELECT id FROM catalog LIMIT 2").fetchall()
    require(len(metadata) == 1 and intent["catalog_id"] == metadata[0]["id"])
    reserve_row = connection.execute("SELECT result FROM operations WHERE id=?",
                                     (scratch["intent_operation"],)).fetchone()
    reserve = json.loads(reserve_row[0])
    _operation(connection, scratch["intent_operation"], "reserve_scratch",
               [token, owner["owner"], reserve["previous_revision"], intent])
    if scratch["state"] == "held":
        held = json.loads(connection.execute("SELECT result FROM operations WHERE id=?",
                                             (scratch["hold_operation"],)).fetchone()[0])
        reason = json.loads(scratch["hold_reason"])
        _operation(connection, scratch["hold_operation"], "hold_scratch",
                   [token, owner["owner"], held["previous_revision"], reason])
    if scratch["workspace_identity"] is None:
        require(scratch["state"] in {"reserved", "held"} and scratch["bind_operation"] is None)
    else:
        identity = json.loads(scratch["workspace_identity"])
        bind_row = connection.execute("SELECT result FROM operations WHERE id=?",
                                      (scratch["bind_operation"],)).fetchone()
        bind = json.loads(bind_row[0])
        _operation(connection, scratch["bind_operation"], "bind_scratch",
                   [token, owner["owner"], bind["previous_revision"], identity,
                    scratch["workspace_stamp"]])
    declarations = {x["name"]: x for x in intent["artifacts"]}
    if scratch["writer_launch"] is None:
        require(scratch["writer_sequence"] is None)
    else:
        writer = connection.execute("SELECT * FROM child_launches WHERE id=?",
                                    (scratch["writer_launch"],)).fetchone()
        require(writer is not None and writer["sequence"] == scratch["writer_sequence"]
                and json.loads(writer["intent"])["access"] == "write"
                and "candidate.mp4" in json.loads(writer["intent"])["outputs"])
    artifacts = connection.execute("SELECT * FROM scratch_artifacts WHERE token=? ORDER BY name LIMIT 32",
                                   (token,)).fetchall()
    require(len(artifacts) == len(declarations) and {x["name"] for x in artifacts} == set(declarations))
    for artifact in artifacts:
        declaration = declarations[artifact["name"]]
        require(artifact["role"] == declaration["role"]
                and bool(artifact["required"]) == declaration["required"])
        if artifact["identity"] is None:
            continue
        op_row = connection.execute("SELECT result FROM operations WHERE id=?",
                                    (artifact["bind_operation"],)).fetchone()
        binding = json.loads(op_row[0])
        observed = next((x for x in binding["artifacts"] if x["name"] == artifact["name"]), None)
        require(observed is not None and json.loads(artifact["identity"]) == observed["identity"]
                and artifact["size"] == observed["size"] and artifact["stamp"] == observed["stamp"])
        _operation(connection, artifact["bind_operation"], "bind_scratch_artifacts",
                   [token, owner["owner"], binding["previous_revision"], binding["launch"],
                    binding["artifacts"]])
    candidate = connection.execute("SELECT * FROM scratch_candidates WHERE token=?", (token,)).fetchone()
    if candidate is None:
        require(scratch["state"] != "candidate_ready")
    else:
        require(scratch["state"] == "candidate_ready" and candidate["validation"] == "not_checked"
                and candidate["publication"] == "unpublished"
                and candidate["launch"] == scratch["writer_launch"]
                and candidate["sequence"] == scratch["writer_sequence"])
        sha256(candidate["sha256"])
        sha256(candidate["seal_hash"])
        sha256(candidate["marker_hash"])
        outcome = json.loads(connection.execute("SELECT result FROM operations WHERE id=?",
                                                (candidate["operation"],)).fetchone()[0])
        _operation(connection, candidate["operation"], "seal_candidate",
                   [token, owner["owner"], outcome["previous_revision"], candidate["launch"],
                    outcome["evidence"]])
        require(outcome["publication"] == "unpublished" and outcome["validation"] == "not_checked")
        evidence = outcome["evidence"]
        require(candidate["name"] == evidence["name"]
                and json.loads(candidate["identity"]) == evidence["identity"]
                and candidate["size"] == evidence["size"] and candidate["stamp"] == evidence["stamp"]
                and candidate["sha256"] == evidence["sha256"]
                and candidate["seal_hash"] == outcome["seal_hash"]
                and candidate["marker_hash"] == outcome["marker_hash"],
                "candidate operation result conflicts with permanent evidence")
        child = connection.execute("SELECT sequence,exit,diagnostics,cleanup FROM child_launches WHERE id=?",
                                   (candidate["launch"],)).fetchone()
        require(child is not None and child["sequence"] == candidate["sequence"]
                and json.loads(child["exit"])["code"] == 0 and child["cleanup"] == 1
                and json.loads(child["diagnostics"])["complete"], "candidate writer receipt chain conflicts")
    latest_row = connection.execute("SELECT kind,result FROM operations WHERE id=?",
                                    (scratch["latest_operation"],)).fetchone()
    require(latest_row is not None and json.loads(latest_row["result"])["token"] == token
            and json.loads(latest_row["result"])["owner"] == owner["owner"])
    allowed = {"reserved": {"reserve_scratch"}, "bound": {"bind_scratch", "bind_scratch_artifacts"},
               "held": {"hold_scratch"}, "candidate_ready": {"seal_candidate"}}
    require(latest_row["kind"] in allowed[scratch["state"]], "scratch latest operation/state conflicts")
    if candidate is not None:
        candidate_artifact = next((item for item in artifacts if item["name"] == candidate["name"]), None)
        execution = json.loads(candidate["execution"])
        writer = connection.execute("SELECT * FROM child_launches WHERE id=?",
                                    (candidate["launch"],)).fetchone()
        exit_record = json.loads(writer["exit"])
        diagnostics = json.loads(writer["diagnostics"])
        require(candidate_artifact is not None and candidate["name"] == "candidate.mp4"
                and candidate["seal_hash"] == owner["seal_hash"]
                and candidate["marker_hash"] == owner["marker_hash"]
                and json.loads(candidate_artifact["identity"]) == json.loads(candidate["identity"])
                and candidate_artifact["size"] == candidate["size"]
                and candidate_artifact["stamp"] == candidate["stamp"]
                and execution == {"launch": candidate["launch"], "sequence": candidate["sequence"],
                    "exit": exit_record, "diagnostics": digest(diagnostics),
                    "cleanup": writer["cleanup"], "input_decode": outcome["evidence"]["input_decode"]},
                "candidate execution/binding evidence conflicts")
