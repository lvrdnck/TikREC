"""Immutable pending assembly control; a marker alone never releases a capture."""

import json
import os
from dataclasses import asdict
from pathlib import Path

from .session_journal_types import digest, encode, identifier, require, sha256


MARKER_NAME = "finalization-owner.json"


def marker_values(authority, intent, binding, operation, seal):
    """Bind one durable operation to the known catalog and original pending output."""
    return {"schema_version": 1, "catalog_id": authority.journal.catalog_id,
            "catalog_native": asdict(authority.catalog.identity),
            "catalog_file": authority.catalog.initial.split(":")[:2],
            "session_id": intent.session_id, "generation": binding["generation"],
            "revision": binding["revision"], "operation": operation,
            "intent_hash": digest(asdict(intent)), "seal_hash": digest(asdict(seal)),
            "disposition": seal.disposition, "requested_output": intent.output_path,
            "raw_copy": intent.raw_copy}


def persist_marker(path, values):
    """Exclusively persist control intent, retaining even a failed write as evidence."""
    with Path(path).open("x", encoding="utf-8") as handle:
        handle.write(encode(values) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def inspect_pending(authority, session_id):
    """Distinguish committed ownership from held capture without launching a source."""
    identifier(session_id)
    authority.assert_held()
    authority.journal.status()
    row = authority.journal.session(session_id)
    require(row is not None, "unknown pending session")
    path = Path(row["intent"]["parts_path"]) / MARKER_NAME
    if not path.exists():
        require(row["phase"] in {"reserved", "capturing", "closing", "no_assembly"},
                "committed pending work lost its marker")
        return {"session_id": session_id, "phase": row["phase"], "source_resume_allowed": False}
    from .capture_handoff_native import NativeHandle
    with NativeHandle(path) as held:
        values = json.loads(held.read_control())
    validate_pending_control(authority, session_id, row, values)
    receipt = authority.journal.operation(values["operation"])
    phase = validate_pending_values(authority, session_id, row, values, receipt)
    return {"session_id": session_id, "phase": phase, "operation": values["operation"],
            "source_resume_allowed": False}


def validate_pending_control(authority, session_id, row, values):
    """Refuse invalid control/disposition bindings before looking up any receipt."""
    require(type(values) is dict, "unsupported pending marker")
    require(set(values) == {"schema_version", "catalog_id", "catalog_native", "catalog_file", "session_id",
                           "generation", "revision", "operation", "intent_hash", "seal_hash", "disposition",
                           "requested_output", "raw_copy"}, "unsupported pending marker fields")
    identifier(values["operation"])
    sha256(values["seal_hash"])
    require(type(values["disposition"]) is str and values["disposition"] in {"assembly", "empty"},
            "unsupported pending marker disposition")
    # The persisted seal fixes the disposition independently of operation receipts.
    require(row["seal"] is None or values["disposition"] == row["seal"]["disposition"],
            "pending marker disposition conflicts with committed seal")
    require(type(values["schema_version"]) is int and values["schema_version"] == 1
            and values["catalog_id"] == authority.journal.catalog_id
            and digest(values["catalog_native"]) == digest(asdict(authority.catalog.identity))
            and values["catalog_file"] == authority.catalog.initial.split(":")[:2]
            and values["session_id"] == session_id and values["generation"] == row["generation"]
            and type(values["generation"]) is int and type(values["revision"]) is int
            and values["revision"] > 0
            and values["intent_hash"] == digest(row["intent"])
            and values["requested_output"] == row["intent"]["output_path"]
            and type(values["raw_copy"]) is bool
            and values["raw_copy"] == row["intent"]["raw_copy"], "pending marker authority conflicts")


def validate_pending_values(authority, session_id, row, values, receipt):
    """Validate held marker values against an explicit same-catalog row and receipt."""
    validate_pending_control(authority, session_id, row, values)
    if receipt is None:
        require(row["phase"] == "closing", "uncommitted marker lacks capture responsibility")
        phase = "closing"
    else:
        result = json.loads(receipt["result"])
        expected_kind = "handoff" if values["disposition"] == "assembly" else "settle_empty_capture"
        require(receipt["kind"] == expected_kind and result["session_id"] == session_id
                and result["seal_hash"] == values["seal_hash"] == row["seal_hash"]
                and result["generation"] == values["generation"]
                and result["revision"] == values["revision"] + 1, "pending receipt binding conflicts")
        phase = row["phase"]
    return phase
