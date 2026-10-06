"""Append-only validation authority and receipts; candidates remain immutable."""

import json
from pathlib import Path

from .candidate_validation_plan import binding_commands
from .candidate_validation_report import check_report
from .session_journal_owned import advance
from .session_journal_owned_view import owner_guard
from .session_journal_types import digest, encode, identifier, require


class ValidationOperations:
    """One validation phase for the original live candidate; no retry or adoption."""

    def begin_validation(self, operation, token, owner, revision, binding):
        """Reserve three exact read-only launches against immutable assembly evidence."""
        require(type(binding) is dict and set(binding) in ({"session_id", "token", "candidate", "commands", "workspace"},
                {"session_id", "token", "candidate", "commands", "workspace", "transport"})
                and binding.get("transport", "path") in {"path", "retained_stdin"})
        def action(connection):
            row = owner_guard(connection, token, owner, revision, launch=True)
            scratch = row["scratch"]
            candidate = None if scratch is None else scratch["candidate"]
            require(candidate is not None and row["child"]["id"] == candidate["launch"]
                    and binding["candidate"] == candidate and binding["session_id"] == row["session_id"]
                    and binding["token"] == token and binding["workspace"] == scratch["intent"]["workspace_path"],
                    "validation lacks exact same-attempt candidate")
            executable = Path(binding["commands"][0][0])
            require(executable.is_absolute() and executable.suffix.casefold() == ".exe"
                    and binding["commands"] == binding_commands(binding),
                    "validation requires fixed media checks")
            connection.execute("INSERT INTO candidate_validations VALUES (?,?,?)", (token, encode(binding), operation))
            return {**advance(connection, operation, row), "binding": binding}
        return self._mutate(operation, "begin_validation", [token, owner, revision, binding], action)

    def finish_validation(self, operation, token, owner, revision, evidence):
        """Append a semantic outcome after exact native cleanup and full diagnostics."""
        require(type(evidence) is dict and set(evidence) == {"report", "children", "binding_hash"}
                and type(evidence["report"]) is dict and type(evidence["report"].get("passed")) is bool)
        def action(connection):
            row = owner_guard(connection, token, owner, revision, launch=True)
            authority = connection.execute("SELECT * FROM candidate_validations WHERE token=?", (token,)).fetchone()
            require(authority is not None, "validation authority missing")
            binding = json.loads(authority["binding"])
            check_report(evidence["report"], binding)
            require(evidence["binding_hash"] == digest(binding), "validation binding changed")
            children = validation_children(connection, binding)
            require(len(children) == 3 and row["sequence"] == binding["candidate"]["sequence"] + 3
                    and evidence["children"] == children, "validation execution incomplete")
            for child in children:
                require(child["exit"] is not None and child["exit"]["state"] == "confirmed_exited"
                        and child["exit"]["active"] == 0 and child["cleanup"] == 1
                        and child["diagnostics"] is not None and child["diagnostics"]["complete"],
                        "validation native/diagnostic cleanup incomplete")
            if evidence["report"]["passed"]:
                require(all(c["exit"]["code"] == 0 and c["diagnostics"]["counts"]["stderr"] == 0 for c in children)
                        and evidence["report"].get("final_output_inspection") == "passed"
                        and evidence["report"].get("final_output_decode") == "passed"
                        and evidence["report"].get("packet_dts") == "passed", "validation success lacks media proof")
            connection.execute("INSERT INTO validation_receipts VALUES (?,?,?)", (token, encode(evidence), operation))
            return {**advance(connection, operation, row), "evidence": evidence, "publication": "unpublished"}
        return self._mutate(operation, "finish_validation", [token, owner, revision, evidence], action)

    def validation(self, token):
        """Inspect evidence only; reopening never creates validation permission."""
        identifier(token)
        def read(connection):
            self._audit(connection)
            authority = connection.execute("SELECT * FROM candidate_validations WHERE token=?", (token,)).fetchone()
            if authority is None:
                return None
            receipt = connection.execute("SELECT * FROM validation_receipts WHERE token=?", (token,)).fetchone()
            return {"binding": json.loads(authority["binding"]), "operation": authority["operation"],
                    "receipt_operation": None if receipt is None else receipt["operation"],
                    "evidence": None if receipt is None else json.loads(receipt["evidence"])}
        return self._read(read)


def validation_children(connection, binding):
    """Return at most the three exact validator executions with immutable receipts."""
    children = []
    for row in connection.execute("SELECT * FROM child_launches WHERE token=? AND sequence>? ORDER BY sequence LIMIT 4",
                                  (binding["token"], binding["candidate"]["sequence"])):
        child = dict(row)
        for field in ("intent", "identity", "exit", "diagnostics"):
            child[field] = None if child[field] is None else json.loads(child[field])
        children.append(child)
    return children
