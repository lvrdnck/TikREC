"""Immutable publication preparation and observed facts, without task settlement."""

import json
from contextlib import contextmanager

from .session_journal_owned import advance
from .session_journal_owned_view import owner_guard
from .session_journal_types import digest, encode, identifier, require


def validation_view(connection, token):
    """Project exact authority/receipt rows without constructing live permission."""
    authority = connection.execute("SELECT * FROM candidate_validations WHERE token=?", (token,)).fetchone()
    result = connection.execute("SELECT * FROM validation_receipts WHERE token=?", (token,)).fetchone()
    require(authority is not None and result is not None, "successful validation required")
    return {"binding": json.loads(authority["binding"]), "operation": authority["operation"],
            "receipt_operation": result["operation"], "evidence": json.loads(result["evidence"])}


def check_binding(connection, row, binding, *, historical=False):
    """Bind preparation to original H, immutable candidate/validation and exact claim."""
    require(type(binding) is dict and set(binding) == {"session_id", "token", "owner", "h_operation",
        "h_revision", "seal_hash", "marker_hash", "candidate", "validation", "destination", "inventory", "workspace"},
        "invalid publication binding")
    for key in ("session_id", "token", "owner", "h_operation", "h_revision", "seal_hash", "marker_hash"):
        require(binding[key] == row[key], "publication original ownership conflicts")
    scratch = row["scratch"]
    validation = validation_view(connection, row["token"])
    require(scratch is not None and binding["candidate"] == scratch["candidate"]
            and binding["workspace"] == scratch["workspace_identity"]
            and binding["validation"] == validation and validation["evidence"]["report"]["passed"]
            and validation["binding"].get("transport") == "retained_stdin"
            and row["sequence"] == scratch["candidate"]["sequence"] + 3,
            "publication lacks exact successful protected validation")
    expected = [{"name": a["name"], "identity": json.loads(a["identity"]),
                 "size": a["size"], "stamp": a["stamp"]} for a in scratch["artifacts"] if a["identity"] is not None]
    require(binding["inventory"] == expected, "publication inventory conflicts")
    session = connection.execute("SELECT intent FROM sessions WHERE id=?", (row["session_id"],)).fetchone()
    intent = json.loads(session[0])
    destination = binding["destination"]
    require(set(destination) == {"path", "identity", "parent", "parent_stamp"}
            and destination["path"] == intent["output_path"] and destination["identity"] == intent["output"]
            and destination["parent"] == intent["root"]
            and type(destination["parent_stamp"]) is str and len(destination["parent_stamp"]) <= 256,
            "publication destination conflicts")
    if not historical:
        claims = connection.execute("SELECT session FROM artifacts WHERE identity=?", (encode(intent["output"]),)).fetchall()
        require(len(claims) == 1 and claims[0][0] == row["session_id"], "publication claim conflicts")


def check_result(binding, operation, evidence):
    """Observed publication is separate from preparation and immutable media proof."""
    candidate = binding["candidate"]
    require(evidence == {"state": "observed_published", "preparation_operation": operation,
        "binding_hash": digest(binding), "identity": binding["destination"]["identity"],
        "size": candidate["size"], "stamp": candidate["stamp"], "sha256": candidate["sha256"]},
        "publication result conflicts")


class PublicationOperations:
    """Append facts only; durable records alone never authorize another native move."""

    def prepare_publication(self, operation, token, owner, revision, binding):
        """Persist exact evidence before native transition, leaving completion unknown."""
        def action(connection):
            row = owner_guard(connection, token, owner, revision, launch=True)
            check_binding(connection, row, binding)
            connection.execute("INSERT INTO publication_preparations VALUES (?,?,?)", (token, encode(binding), operation))
            return {**advance(connection, operation, row), "binding": binding, "state": "prepared"}
        return self._mutate(operation, "prepare_publication", [token, owner, revision, binding], action)

    def observe_publication(self, operation, token, owner, revision, evidence):
        """Append observed native/post-proof result without completing or releasing work."""
        def action(connection):
            row = owner_guard(connection, token, owner, revision, launch=True)
            preparation = connection.execute("SELECT * FROM publication_preparations WHERE token=?", (token,)).fetchone()
            require(preparation is not None, "publication preparation missing")
            check_result(json.loads(preparation["binding"]), preparation["operation"], evidence)
            connection.execute("INSERT INTO publication_results VALUES (?,?,?)", (token, encode(evidence), operation))
            return {**advance(connection, operation, row), "evidence": evidence}
        return self._mutate(operation, "observe_publication", [token, owner, revision, evidence], action)

    @contextmanager
    def publication_fence(self, token, owner, revision, operation, binding_hash):
        """Fence the single native rename against committed revocation, with no scans."""
        connection = self._connect()
        try:
            connection.execute("BEGIN")
            owner_guard(connection, token, owner, revision, launch=True)
            row = connection.execute("SELECT * FROM publication_preparations WHERE token=?", (token,)).fetchone()
            require(row is not None and row["operation"] == operation and digest(json.loads(row["binding"])) == binding_hash
                    and connection.execute("SELECT 1 FROM publication_results WHERE token=?", (token,)).fetchone() is None,
                    "stale publication preparation")
            yield
        finally:
            connection.close()

    def publication(self, token):
        """Report only committed preparation/result; never infer rename or adoption."""
        identifier(token)
        def read(connection):
            self._audit(connection)
            from .session_journal_owned_view import audit_history
            audit_history(connection, token)
            row = connection.execute("SELECT * FROM publication_preparations WHERE token=?", (token,)).fetchone()
            if row is None:
                return None
            result = connection.execute("SELECT * FROM publication_results WHERE token=?", (token,)).fetchone()
            return {"binding": json.loads(row["binding"]), "operation": row["operation"],
                    "result_operation": None if result is None else result["operation"],
                    "evidence": None if result is None else json.loads(result["evidence"])}
        return self._read(read)
