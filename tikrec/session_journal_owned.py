"""Permanent one-shot attempt/child records; no scheduling or success settlement."""

import json
import re
from pathlib import Path

from .session_journal_owned_view import OwnedViews, owner_guard
from .session_journal_tasks import claim
from .session_journal_types import encode, identifier, require, sha256


def advance(connection, operation, row):
    """Advance the independent attempt revision, leaving the original H untouched."""
    connection.execute("UPDATE attempt_owners SET revision=revision+1,last_operation=? WHERE token=?",
                       (operation, row["token"]))
    return {"session_id": row["session_id"], "token": row["token"], "owner": row["owner"],
            "previous_revision": row["revision"], "revision": row["revision"] + 1,
            "operation": operation}


class OwnedOperations(OwnedViews):
    """Guarded durable authority for a held, unfinished single finalizer attempt."""

    def claim_owned(self, operation, token, owner):
        """Atomically use existing FIFO rules and bind a new local one-shot owner."""
        identifier(token)
        identifier(owner)
        def action(connection):
            result = claim(connection, token)
            if result is None:
                return None
            sid = result["session_id"]
            # The first queue receipt remains original H even after an explicit retry.
            entry = connection.execute("SELECT * FROM queue_entries WHERE session=? "
                                       "ORDER BY position LIMIT 1", (sid,)).fetchone()
            receipt = connection.execute("SELECT * FROM operations WHERE id=?",
                                         (entry["operation"],)).fetchone()
            h = json.loads(receipt["result"])
            require(receipt["kind"] == "handoff" and h["session_id"] == sid,
                    "owned claim lacks original H")
            connection.execute("INSERT INTO attempt_owners VALUES (?,?,1,'held',?,?,?,?,NULL,0,?)",
                (token, owner, operation, entry["operation"], h["revision"], h["seal_hash"], operation))
            return {**result, "task_revision": result["revision"], "revision": 1,
                    "owner": owner, "operation": operation}
        return self._mutate(operation, "claim_owned", [token, owner], action)

    def bind_owned_inputs(self, operation, token, owner, revision, marker_hash):
        """Persist an attempt-time marker observation, never a retroactive H hash."""
        sha256(marker_hash)
        def action(connection):
            row = owner_guard(connection, token, owner, revision)
            require(row["state"] == "held" and row["marker_hash"] is None and row["sequence"] == 0,
                    "inputs already bound or revoked")
            connection.execute("UPDATE attempt_owners SET marker_hash=? WHERE token=?", (marker_hash, token))
            return advance(connection, operation, row)
        return self._mutate(operation, "bind_owned_inputs", [token, owner, revision, marker_hash], action)

    def launch_intent(self, operation, token, owner, revision, launch, intent):
        """Commit permanent sequential executable/argv/seal intent before native creation."""
        identifier(launch)
        read_keys = {"executable", "arguments", "cwd", "phase", "seal_hash", "marker_hash", "predecessor"}
        write_keys = read_keys | {"access", "outputs"}
        validation_keys = read_keys | {"access", "validation_operation", "validation_index"}
        require(type(intent) is dict and frozenset(intent) in
                {frozenset(read_keys), frozenset(write_keys), frozenset(validation_keys)},
                "invalid child intent")
        validation = set(intent) == validation_keys
        if validation:
            require(intent["access"] == "candidate_validation" and type(intent["validation_index"]) is int)
            identifier(intent["validation_operation"])
        elif "access" in intent:
            require(intent["access"] == "write" and type(intent["outputs"]) is list
                    and 1 <= len(intent["outputs"]) <= 32
                    and len(intent["outputs"]) == len(set(intent["outputs"]))
                    and "candidate.mp4" in intent["outputs"]
                    and all(type(name) is str and re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,63}", name)
                            for name in intent["outputs"]), "invalid declared writer artifacts")
        require(type(intent["phase"]) is str and re.fullmatch(r"[a-z_]{1,64}", intent["phase"]) is not None)
        require(type(intent["arguments"]) is list and all(type(a) is str and "\0" not in a
                for a in intent["arguments"]), "invalid child arguments")
        require(type(intent["executable"]) is str and Path(intent["executable"]).is_absolute()
                and Path(intent["executable"]).suffix.casefold() == ".exe"
                and type(intent["cwd"]) is str and Path(intent["cwd"]).is_absolute(),
                "explicit launch paths required")
        def action(connection):
            row = owner_guard(connection, token, owner, revision, launch=True)
            prior = row["child"]
            if validation:
                from .candidate_validation_plan import check_launch
                check_launch(connection, row, intent)
            else:
                require(connection.execute("SELECT 1 FROM scratch_candidates WHERE token=?", (token,)).fetchone()
                        is None, "candidate-ready attempt cannot launch another child")
            if intent.get("access") == "write":
                scratch = connection.execute("SELECT * FROM scratch_owners WHERE token=?", (token,)).fetchone()
                require(scratch is not None and scratch["state"] == "bound"
                        and scratch["writer_launch"] is None
                        and set(intent["outputs"]) <= {x["name"] for x in connection.execute(
                            "SELECT name FROM scratch_artifacts WHERE token=?", (token,))}
                        and Path(intent["cwd"]) == Path(json.loads(scratch["intent"])["workspace_path"]),
                        "writer lacks bound attempt scratch and declared outputs")
            require(intent["seal_hash"] == row["seal_hash"] and intent["marker_hash"] == row["marker_hash"]
                    and intent["predecessor"] == (None if prior is None else prior["id"]),
                    "child input/predecessor binding conflicts")
            if prior is not None:
                require(prior["exit"] is not None and prior["cleanup"] == 1
                        and prior["diagnostics"] is not None and prior["diagnostics"]["complete"],
                        "prior child lifetime, cleanup or diagnostics unresolved")
            sequence = row["sequence"] + 1
            connection.execute("INSERT INTO child_launches(id,token,sequence,intent,intent_operation) "
                               "VALUES (?,?,?,?,?)", (launch, token, sequence, encode(intent), operation))
            if intent.get("access") == "write":
                connection.execute("UPDATE scratch_owners SET writer_launch=?,writer_sequence=? WHERE token=?",
                                   (launch, sequence, token))
            connection.execute("UPDATE attempt_owners SET sequence=? WHERE token=?", (sequence, token))
            return {**advance(connection, operation, row), "launch": launch, "sequence": sequence}
        return self._mutate(operation, "launch_intent", [token, owner, revision, launch, intent], action)

    def child_record(self, operation, token, owner, revision, launch, field, value):
        """Record identity, whole-job exit, streams or local cleanup independently."""
        identifier(launch)
        require(field in {"identity", "exit", "diagnostics", "cleanup"}, "invalid child record")
        def action(connection):
            row = owner_guard(connection, token, owner, revision, launch=field == "identity")
            child = row["child"]
            require(child is not None and child["id"] == launch and child[field] in (None, 0),
                    "stale or duplicate child record")
            if field == "identity":
                require(type(value) is dict and set(value) == {"session_id", "attempt_token", "pid",
                        "created", "image"} and value["session_id"] == row["session_id"]
                        and value["attempt_token"] == token and type(value["pid"]) is int
                        and value["pid"] > 0 and type(value["created"]) is int
                        and value["created"] > 0 and type(value["image"]) is str,
                        "invalid native identity")
                require(value["image"].casefold() == child["intent"]["executable"].casefold(),
                        "native executable conflicts with durable intent")
            elif field == "exit":
                require(type(value) is dict and set(value) == {"state", "identity", "code", "active"}
                        and value["state"] in {"not_created", "confirmed_exited"}, "unknown child lifetime")
                require((value["state"] == "not_created" and value["identity"] is None
                         and child["identity"] is None) or
                        (value["state"] == "confirmed_exited" and value["active"] == 0
                         and type(value["code"]) is int and value["identity"] is not None
                         and (child["identity"] is None or value["identity"] == child["identity"])),
                        "native exit identity conflicts")
            elif field == "diagnostics":
                require(child["exit"] is not None and type(value) is dict
                        and type(value.get("complete")) is bool, "diagnostics lack exit proof")
            else:
                require(value == 1 and child["exit"] is not None, "cleanup lacks whole-job exit")
            # Column names come only from the fixed internal allowlist above.
            connection.execute(f"UPDATE child_launches SET {field}=?,{field}_operation=? WHERE id=?",
                               (value if field == "cleanup" else encode(value), operation, launch))
            return {**advance(connection, operation, row), "launch": launch, "field": field}
        return self._mutate(operation, "child_" + field, [token, owner, revision, launch, value], action)

    def revoke_owned(self, operation, token, owner, revision):
        """Irreversibly revoke future execution while retaining task/unit/input claims."""
        def action(connection):
            row = owner_guard(connection, token, owner, revision)
            require(row["state"] == "held", "owned attempt already revoked")
            connection.execute("UPDATE attempt_owners SET state='revoked' WHERE token=?", (token,))
            return advance(connection, operation, row)
        return self._mutate(operation, "revoke_owned", [token, owner, revision], action)
