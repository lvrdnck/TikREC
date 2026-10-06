"""Audit publication records without filesystem access or recovery authority."""

import json

from .session_journal_owned_checks import receipt
from .session_journal_publication import check_binding, check_result
from .session_journal_types import digest, require


def audit_publication(connection, owner):
    """Preparation never implies completion; each optional result has its own receipt."""
    prepared = connection.execute("SELECT * FROM publication_preparations WHERE token=?", (owner["token"],)).fetchone()
    if prepared is None:
        return
    binding = json.loads(prepared["binding"])
    check_binding(connection, owner, binding)
    op, result = receipt(connection, prepared["operation"], "prepare_publication")
    prepared_result = result
    validation_operation = connection.execute("SELECT result FROM operations WHERE id=?",
        (binding["validation"]["receipt_operation"],)).fetchone()
    require(validation_operation is not None and result["previous_revision"] == json.loads(validation_operation[0])["revision"]
            and result["operation"] == prepared["operation"] and result["session_id"] == owner["session_id"]
            and result["revision"] == result["previous_revision"] + 1, "publication preparation ordering conflicts")
    require(result["binding"] == binding and result["state"] == "prepared"
            and result["token"] == owner["token"] and result["owner"] == owner["owner"]
            and op["arguments_hash"] == digest([owner["token"], owner["owner"], result["previous_revision"], binding]),
            "publication preparation receipt conflicts")
    observed = connection.execute("SELECT * FROM publication_results WHERE token=?", (owner["token"],)).fetchone()
    if observed is not None:
        evidence = json.loads(observed["evidence"])
        check_result(binding, prepared["operation"], evidence)
        op, result = receipt(connection, observed["operation"], "observe_publication")
        require(result["previous_revision"] == prepared_result["revision"]
                and result["operation"] == observed["operation"] and result["session_id"] == owner["session_id"]
                and result["revision"] == result["previous_revision"] + 1, "publication result ordering conflicts")
        require(result["evidence"] == evidence and result["token"] == owner["token"]
                and result["owner"] == owner["owner"] and op["arguments_hash"] == digest([
                    owner["token"], owner["owner"], result["previous_revision"], evidence]),
                "publication observation receipt conflicts")
