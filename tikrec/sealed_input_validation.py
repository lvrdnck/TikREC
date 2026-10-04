"""Bindings and inventory checks for a committed, explicitly addressed H seal."""

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from .capture_handoff_inventory import _inventory_order, _role
from .capture_handoff_marker import MARKER_NAME, validate_pending_values
from .session_journal_types import (ClosureSeal, SessionIntent, closure_from_record, digest,
                                   encode, intent_from_record, require)


@dataclass(frozen=True)
class SealedInputEvidence:
    """Immutable metadata snapshot valid only while its guard remains held."""

    session_id: str
    revision: int
    seal_hash: str
    intent: SessionIntent
    seal: ClosureSeal
    flv_inputs: tuple[Path, ...]
    marker_sha256: str


def target_binding(row, session_id, revision, seal_hash):
    """Require the original queued H owner; this grants neither claim nor launch."""
    require(row is not None and row["id"] == session_id and row["revision"] == revision
            and row["seal_hash"] == seal_hash and row["phase"] == "queued",
            "stale or uncommitted sealed input binding")
    task, queue, receipt = row["task"], row["queue"], row["receipt"]
    require(task is not None and task["state"] == "queued" and task["revision"] == 1
            and task["attempt"] == 0 and task["token"] is None
            and queue is not None and task["queue_order"] == queue["position"],
            "sealed input task/H owner conflicts")
    return original_h_binding(row, revision, queue, receipt)


def original_h_binding(row, revision, queue, receipt):
    """Validate immutable H evidence separately from later task/attempt revisions."""
    session_id, seal_hash = row["id"], row["seal_hash"]
    intent, seal = intent_from_record(encode(row["intent"])), closure_from_record(encode(row["seal"]))
    require(seal.disposition == "assembly" and digest(asdict(seal)) == seal_hash
            and row["unit"] == {"session": session_id, "kind": "task"} and not row["bound"]
            and receipt is not None and receipt["id"] == queue["operation"]
            and receipt["kind"] == "handoff", "sealed input task/H owner conflicts")
    require(receipt["arguments_hash"] == digest([session_id, row["generation"], revision - 1,
                                               asdict(seal)]), "H receipt arguments conflict")
    result = json.loads(receipt["result"])
    require(result == {"session_id": session_id, "slot": row["origin_slot"],
                       "generation": row["generation"], "revision": revision,
                       "task_revision": 1, "seal_hash": seal_hash, "queue_order": queue["position"]},
            "H receipt result conflicts")
    require(row["artifacts"] == [
        {"session": session_id, "kind": "output", "identity": encode(asdict(intent.output))},
        {"session": session_id, "kind": "parts", "identity": encode(asdict(intent.parts))}],
        "sealed artifact claims conflict")
    require(row["rooms"] == [seal.room_id]
            and tuple(sorted(seal.artifacts, key=_inventory_order)) == seal.artifacts,
            "sealed ordering/room conflicts")
    return intent, seal


def inventory_names(directory, seal):
    """Bound enumeration and reject extras, duplicate aliases or omitted evidence."""
    names = []
    for path in directory.iterdir():
        names.append(path.name.casefold())
        require(len(names) <= 4097, "sealed inventory too large")
    expected = [a.identity.components[-1] for a in seal.artifacts] + [MARKER_NAME]
    require(len(names) == len(set(names)) and sorted(names) == sorted(expected),
            "sealed inventory changed")


def verify_inventory(authority, row, intent, seal, directory, files, marker, *,
                     h_receipt=None, h_revision=None):
    """Check complete held metadata, control hashes and exact marker/H bindings."""
    directory.verify()
    require(directory.identity == intent.parts, "sealed parts identity changed")
    inventory_names(directory.path, seal)
    for artifact, held in zip(seal.artifacts, files, strict=True):
        held.verify()
        require(_role(artifact.identity.components[-1]) == artifact.role
                and held.identity == artifact.identity and held.size == artifact.size
                and held.stamp == artifact.stamp, "sealed artifact metadata changed")
        if artifact.control_hash is not None:
            require(hashlib.sha256(held.read_control()).hexdigest() == artifact.control_hash,
                    "sealed control hash changed")
    marker.verify()
    require(marker.identity.components == intent.parts.components + (MARKER_NAME,)
            and marker.identity.volume == intent.parts.volume, "pending marker namespace conflicts")
    data = marker.read_control()
    values = json.loads(data)
    receipt = row["receipt"] if h_receipt is None else h_receipt
    revision = row["revision"] if h_revision is None else h_revision
    validate_pending_values(authority, intent.session_id, row, values, receipt)
    require(values["operation"] == receipt["id"]
            and values["revision"] + 1 == revision, "pending marker H revision conflicts")
    # Parent pins allow child creation. Reconcile enumeration again after held
    # control reads rather than treating the first list as an atomic namespace.
    inventory_names(directory.path, seal)
    for held in (*files, marker):
        held.verify()
    return hashlib.sha256(data).hexdigest()
