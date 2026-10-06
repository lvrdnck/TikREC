"""Bounded exact validation receipt chain audit, separate from assembly evidence."""

import json
from pathlib import Path

from .candidate_validation_plan import binding_commands
from .candidate_validation_report import check_report
from .session_journal_owned_checks import audit_child, receipt
from .session_journal_types import digest, require
from .session_journal_validation import validation_children


def audit_validation(connection, owner):
    """Prove authority, fixed launch chain and optional immutable validation receipt."""
    authority = connection.execute("SELECT * FROM candidate_validations WHERE token=?", (owner["token"],)).fetchone()
    if authority is None:
        return
    binding = json.loads(authority["binding"])
    op, result = receipt(connection, authority["operation"], "begin_validation")
    require(binding["token"] == owner["token"] and binding["session_id"] == owner["session_id"]
            and binding["candidate"] == owner["scratch"]["candidate"]
            and binding["workspace"] == owner["scratch"]["intent"]["workspace_path"]
            and binding["commands"] == binding_commands(binding)
            and result["binding"] == binding and result["token"] == owner["token"]
            and result["owner"] == owner["owner"] and op["arguments_hash"] == digest([
                owner["token"], owner["owner"], result["previous_revision"], binding]), "validation authority conflicts")
    children = validation_children(connection, binding)
    require(len(children) <= 3, "too many validation launches")
    for index, child in enumerate(children):
        intent = child["intent"]
        require(intent.get("access") == "candidate_validation" and intent["validation_index"] == index
                and intent["validation_operation"] == authority["operation"]
                and intent["phase"] == "candidate_validation" and intent["cwd"] == binding["workspace"]
                and [intent["executable"], *intent["arguments"]] == binding["commands"][index]
                and child["sequence"] == binding["candidate"]["sequence"] + index + 1,
                "validation launch conflicts")
        # Older validation phases also remain receipt-bound, even after later reads.
        raw = dict(child)
        for field in ("intent", "identity", "exit", "diagnostics"):
            raw[field] = None if raw[field] is None else json.dumps(raw[field])
        audit_child(connection, owner, raw)
    finished = connection.execute("SELECT * FROM validation_receipts WHERE token=?", (owner["token"],)).fetchone()
    if finished is not None:
        evidence = json.loads(finished["evidence"])
        check_report(evidence["report"], binding)
        op, result = receipt(connection, finished["operation"], "finish_validation")
        require(len(children) == 3 and evidence["children"] == children
                and evidence["binding_hash"] == digest(binding) and result["evidence"] == evidence
                and result["token"] == owner["token"] and result["owner"] == owner["owner"]
                and result["publication"] == "unpublished" and op["arguments_hash"] == digest([
                    owner["token"], owner["owner"], result["previous_revision"], evidence]),
                "validation receipt conflicts")
        require(all(c["exit"] is not None and c["exit"]["state"] == "confirmed_exited"
                    and c["exit"]["active"] == 0 and c["cleanup"] == 1
                    and c["diagnostics"] is not None and c["diagnostics"]["complete"] for c in children),
                "validation receipt lost native evidence")
        if evidence["report"]["passed"]:
            require(all(c["exit"]["code"] == 0 and c["diagnostics"]["counts"]["stderr"] == 0 for c in children)
                    and all(evidence["report"].get(k) == "passed" for k in
                            ("final_output_inspection", "final_output_decode", "packet_dts")),
                    "validation success conflicts")
