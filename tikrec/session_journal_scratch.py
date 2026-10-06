"""Permanent scratch and unpublished-candidate ownership receipts."""

import json
import re
from pathlib import PureWindowsPath

from .session_journal_owned_view import OwnedViews, owner_guard
from .session_journal_owned import advance
from .session_journal_types import (ArtifactIdentity, encode, identifier, require,
                                    sha256)


def _identity(value):
    """Rebuild a native identity from explicit durable components."""
    require(type(value) is dict and set(value) == {"volume", "components"})
    return ArtifactIdentity(value["volume"], tuple(value["components"]))


class ScratchOperations(OwnedViews):
    """Append-only scratch authority; records do not grant reopen adoption."""

    def reserve_scratch(self, operation, token, owner, revision, intent):
        """Commit exact attempt/session/input scope before exclusive directory creation."""
        identifier(token)
        require(type(intent) is dict and set(intent) == {"catalog_id", "session_id", "h_operation", "h_revision",
            "seal_hash", "marker_hash", "workspace_path", "parent", "workspace", "artifacts"})
        identifier(intent["catalog_id"])
        sha256(intent["seal_hash"])
        sha256(intent["marker_hash"])
        require(type(intent["h_revision"]) is int and intent["h_revision"] > 0
                and PureWindowsPath(intent["workspace_path"]).is_absolute(), "invalid scratch target")
        parent, workspace = _identity(intent["parent"]), _identity(intent["workspace"])
        require(len(workspace.components) == len(parent.components) + 1
                and workspace.components[:-1] == parent.components, "scratch scope escaped media root")
        require(type(intent["artifacts"]) is list and 1 <= len(intent["artifacts"]) <= 32)
        names = [item.get("name") for item in intent["artifacts"] if type(item) is dict]
        require(len(names) == len(intent["artifacts"]) and len(set(names)) == len(names))
        require(sum(item.get("role") == "candidate" and item.get("required") is True
                    for item in intent["artifacts"]) == 1)
        for item in intent["artifacts"]:
            name = item.get("name")
            reserved = name.split(".", 1)[0].casefold() if type(name) is str else ""
            require(set(item) == {"name", "role", "required"}
                    and type(name) is str
                    and re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,63}", name) is not None
                    and name[-1] not in ". "
                    and reserved not in {"con", "prn", "aux", "nul", *(f"com{i}" for i in range(1, 10)),
                                         *(f"lpt{i}" for i in range(1, 10))}
                    and item["role"] in {"candidate", "helper"}
                    and type(item["required"]) is bool
                    and (item["role"] != "candidate" or (item["required"] and name == "candidate.mp4")),
                    "invalid explicit artifact declaration")
        def action(connection):
            row = owner_guard(connection, token, owner, revision, launch=True)
            session = connection.execute("SELECT intent FROM sessions WHERE id=?", (row["session_id"],)).fetchone()
            session_intent = json.loads(session["intent"])
            require(intent["session_id"] == row["session_id"] and intent["h_operation"] == row["h_operation"]
                    and intent["catalog_id"] == self.catalog_id
                    and intent["h_revision"] == row["h_revision"] and intent["seal_hash"] == row["seal_hash"]
                    and intent["marker_hash"] == row["marker_hash"]
                    and parent == _identity(session_intent["root"])
                    and not workspace.overlaps(_identity(session_intent["output"]))
                    and not workspace.overlaps(_identity(session_intent["parts"])),
                    "scratch does not match original attempt scope")
            expected = PureWindowsPath(session_intent["output_path"]).parent / f".tikrec-attempt-{token}"
            require(PureWindowsPath(intent["workspace_path"]) == expected,
                    "caller-selected scratch path refused")
            connection.execute("INSERT INTO scratch_owners(token,owner,session,intent,state,intent_operation,latest_operation) "
                               "VALUES (?,?,?,?,'reserved',?,?)",
                               (token, owner, row["session_id"], encode(intent), operation, operation))
            connection.executemany("INSERT INTO scratch_artifacts(token,name,role,required) VALUES (?,?,?,?)",
                [(token, item["name"], item["role"], int(item["required"])) for item in intent["artifacts"]])
            return {**advance(connection, operation, row), "state": "reserved"}
        return self._mutate(operation, "reserve_scratch", [token, owner, revision, intent], action)

    def bind_scratch(self, operation, token, owner, revision, identity, stamp):
        """Bind the created directory's observed volume/file identity to its intent."""
        selected = _identity(identity)
        require(type(stamp) is str and 1 <= len(stamp) <= 256)
        def action(connection):
            row = owner_guard(connection, token, owner, revision, launch=True)
            scratch = connection.execute("SELECT * FROM scratch_owners WHERE token=?", (token,)).fetchone()
            intent = json.loads(scratch["intent"])
            require(scratch["state"] == "reserved" and selected == _identity(intent["workspace"]),
                    "workspace creation is ambiguous or substituted")
            connection.execute("UPDATE scratch_owners SET state='bound',workspace_identity=?,workspace_stamp=?,"
                               "bind_operation=?,latest_operation=? WHERE token=?",
                               (encode(identity), stamp, operation, operation, token))
            return {**advance(connection, operation, row), "state": "bound",
                    "identity": identity, "stamp": stamp}
        return self._mutate(operation, "bind_scratch", [token, owner, revision, identity, stamp], action)

    def bind_scratch_artifacts(self, operation, token, owner, revision, launch, artifacts):
        """Bind observed helper/output identities after successful complete writer exit."""
        identifier(launch)
        require(type(artifacts) is list and 1 <= len(artifacts) <= 32)
        for item in artifacts:
            require(type(item) is dict and set(item) == {"name", "identity", "size", "stamp"}
                    and type(item["name"]) is str and type(item["size"]) is int and item["size"] >= 0
                    and type(item["stamp"]) is str, "invalid observed scratch artifact")
            _identity(item["identity"])
        def action(connection):
            row = owner_guard(connection, token, owner, revision)
            scratch = connection.execute("SELECT * FROM scratch_owners WHERE token=?", (token,)).fetchone()
            child = row["child"]
            require(scratch["state"] == "bound" and child is not None and child["id"] == launch
                    and scratch["writer_launch"] == launch and scratch["writer_sequence"] == child["sequence"]
                    and child["exit"] is not None and child["exit"]["state"] == "confirmed_exited"
                    and child["exit"]["code"] == 0 and child["cleanup"] == 1
                    and child["diagnostics"] is not None and child["diagnostics"]["complete"]
                    and child["intent"]["access"] == "write"
                    and child["intent"]["outputs"] == [x["name"] for x in artifacts],
                    "artifacts lack complete authorized writer evidence")
            intent = json.loads(scratch["intent"])
            observed = {x["name"]: x for x in artifacts}
            declarations = {x["name"]: x for x in intent["artifacts"]}
            require(set(observed) <= set(declarations)
                    and {n for n, x in declarations.items() if x["required"]} <= set(observed),
                    "undeclared or missing scratch artifact")
            for name, item in observed.items():
                identity = _identity(item["identity"])
                expected = _identity(intent["workspace"])
                require(identity.volume == expected.volume and identity.components[:-1] == expected.components
                        and identity.components[-1] == name, "scratch artifact escaped owned directory")
                connection.execute("UPDATE scratch_artifacts SET identity=?,size=?,stamp=?,bind_operation=? "
                    "WHERE token=? AND name=? AND identity IS NULL",
                    (encode(item["identity"]), item["size"], item["stamp"], operation, token, name))
            connection.execute("UPDATE scratch_owners SET latest_operation=? WHERE token=?", (operation, token))
            return {**advance(connection, operation, row), "launch": launch, "artifacts": artifacts}
        return self._mutate(operation, "bind_scratch_artifacts",
                            [token, owner, revision, launch, artifacts], action)

    def seal_candidate(self, operation, token, owner, revision, launch, evidence):
        """Persist explicitly unpublished candidate evidence after complete execution proof."""
        identifier(launch)
        require(type(evidence) is dict and set(evidence) == {"name", "identity", "size", "stamp",
            "sha256", "input_decode", "diagnostics_hash"})
        _identity(evidence["identity"])
        sha256(evidence["sha256"])
        sha256(evidence["diagnostics_hash"])
        require(type(evidence["size"]) is int and evidence["size"] > 0
                and evidence["input_decode"] in {"clean", "degraded", "unknown"},
                "invalid candidate evidence")
        def action(connection):
            row = owner_guard(connection, token, owner, revision)
            scratch = connection.execute("SELECT * FROM scratch_owners WHERE token=?", (token,)).fetchone()
            child = row["child"]
            artifact = connection.execute("SELECT * FROM scratch_artifacts WHERE token=? AND name=?",
                                          (token, evidence["name"])).fetchone()
            require(scratch["state"] == "bound" and artifact is not None and artifact["identity"] is not None
                    and scratch["writer_launch"] == launch and scratch["writer_sequence"] == child["sequence"]
                    and _identity(json.loads(artifact["identity"])) == _identity(evidence["identity"])
                    and artifact["size"] == evidence["size"] and artifact["stamp"] == evidence["stamp"]
                    and child is not None and child["id"] == launch and child["sequence"] > 0
                    and child["intent"]["access"] == "write" and evidence["name"] in child["intent"]["outputs"]
                    and child["exit"] is not None and child["exit"]["state"] == "confirmed_exited"
                    and child["exit"]["code"] == 0 and child["exit"]["active"] == 0
                    and child["diagnostics"] is not None and child["diagnostics"]["complete"]
                    and child["cleanup"] == 1, "candidate execution evidence is incomplete")
            require(child["intent"]["seal_hash"] == row["seal_hash"]
                    and child["intent"]["marker_hash"] == row["marker_hash"], "candidate input seal changed")
            execution = {"launch": launch, "sequence": child["sequence"], "exit": child["exit"],
                         "diagnostics": evidence["diagnostics_hash"], "cleanup": child["cleanup"],
                         "input_decode": evidence["input_decode"]}
            connection.execute("INSERT INTO scratch_candidates VALUES (?,?,?,?,?,?,?,?,?,?,?,'not_checked',"
                               "'unpublished',?)", (token, evidence["name"], launch, child["sequence"],
                                encode(evidence["identity"]), evidence["size"], evidence["stamp"],
                                evidence["sha256"], row["seal_hash"], row["marker_hash"],
                                encode(execution), operation))
            connection.execute("UPDATE scratch_owners SET state='candidate_ready',latest_operation=? WHERE token=?",
                               (operation, token))
            return {**advance(connection, operation, row), "launch": launch,
                    "publication": "unpublished", "validation": "not_checked",
                    "seal_hash": row["seal_hash"], "marker_hash": row["marker_hash"],
                    "evidence": evidence}
        return self._mutate(operation, "seal_candidate", [token, owner, revision, launch, evidence], action)

    def hold_scratch(self, operation, token, owner, revision, reason):
        """Permanently mark uncertain/failed scratch as held without cleanup or retry."""
        require(type(reason) is dict and set(reason) == {"first", "secondary"}
                and type(reason["first"]) is str and len(reason["first"]) <= 2048
                and type(reason["secondary"]) is list and len(reason["secondary"]) <= 32
                and all(type(item) is str and len(item) <= 2048 for item in reason["secondary"]),
                "invalid held failure diagnostics")
        def action(connection):
            row = owner_guard(connection, token, owner, revision)
            scratch = connection.execute("SELECT * FROM scratch_owners WHERE token=?", (token,)).fetchone()
            require(scratch is not None and scratch["state"] in {"reserved", "bound"},
                    "scratch cannot be held from its current state")
            connection.execute("UPDATE scratch_owners SET state='held',hold_reason=?,hold_operation=?,"
                               "latest_operation=? WHERE token=?",
                               (encode(reason), operation, operation, token))
            return {**advance(connection, operation, row), "state": "held"}
        return self._mutate(operation, "hold_scratch", [token, owner, revision, reason], action)

    def scratch(self, token):
        """Inspect permanent scratch facts without reopening or adopting native owners."""
        identifier(token)
        def read(connection):
            self._audit(connection)
            from .session_journal_owned_view import audit_history
            audit_history(connection, token)
            owner = connection.execute("SELECT * FROM scratch_owners WHERE token=?", (token,)).fetchone()
            if owner is None:
                return None
            result = dict(owner)
            result["intent"] = json.loads(owner["intent"])
            result["artifacts"] = [dict(x) for x in connection.execute(
                "SELECT * FROM scratch_artifacts WHERE token=? ORDER BY name LIMIT 32", (token,))]
            result["candidate"] = connection.execute("SELECT * FROM scratch_candidates WHERE token=?",
                                                       (token,)).fetchone()
            if result["candidate"] is not None:
                result["candidate"] = dict(result["candidate"])
                for key in ("identity", "execution"):
                    result["candidate"][key] = json.loads(result["candidate"][key])
            return result
        return self._read(read)
