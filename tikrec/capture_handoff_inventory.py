"""Seal actual closed capture artifacts without hashing media on the capture path."""

import hashlib
import json
import re
from pathlib import Path

from .capture_handoff_native import NativeHandle
from .network_evidence import validate_network_record
from .session_journal_types import ClosedArtifact, ClosureSeal, require
from .session_parts import part_order


def _role(name):
    if name == "session.json":
        return "manifest"
    if name == "connections.jsonl":
        return "connections"
    for role, pattern in (("flv", r"part-[0-9]{4,}\.flv"), ("raw", r"connection-[0-9]{4,}\.raw"),
                          ("arrivals", r"connection-[0-9]{4,}\.arrivals\.jsonl")):
        if re.fullmatch(pattern, name):
            return role
    raise ValueError("unexplained retained capture evidence")


def _coalesced_recovery(records, session_id):
    """Count omitted resolver attempts only inside valid, closed outage summaries."""
    active, omitted = False, 0
    for record in records:
        if record.get("event") != "network_recovery":
            continue
        validate_network_record(record, session_id)
        if record["phase"] == "entered":
            require(not active and record["retry_attempt"] == 1, "outage entry conflicts")
            active = True
        else:
            require(active and record["phase"] in {"recovered", "offline", "live_changed", "user_stop"},
                    "capture recovery is failed or ambiguous")
            omitted += record["retry_attempt"] - 1
            active = False
    require(not active, "capture recovery evidence is still open")
    return omitted


def _inventory_order(artifact):
    """Keep source numbering chronological even when names exceed four digits."""
    name = artifact.identity.components[-1]
    if artifact.role == "flv":
        return (0, part_order(Path(name)), 0)
    if artifact.role in {"raw", "arrivals"}:
        # Lexical order reverses 9999/10000; each raw copy precedes its sidecar.
        return (1, int(name.split("-")[1].split(".")[0]), artifact.role == "arrivals")
    return (2, artifact.role, 0)


def closed_inventory(stack, intent, generation, result, warnings, source_items, *, fault=lambda _: None):
    """Hold, flush and bind the complete inventory through H, including failed raw remnants."""
    directory = Path(intent.parts_path)
    parent = stack.enter_context(NativeHandle(directory, directory=True))
    require(parent.identity == intent.parts, "parts native identity changed")
    names = tuple(sorted(directory.iterdir(), key=lambda p: p.name))
    require(2 <= len(names) <= 4096, "capture inventory is missing or too large")
    handles, controls, artifacts = {}, {}, []
    for path in names:
        role = _role(path.name)
        require(intent.raw_copy or role not in {"raw", "arrivals"}, "raw policy conflicts")
        held = stack.enter_context(NativeHandle(path))
        require(intent.parts.contains(held.identity), "input native identity is outside parts")
        handles[path.name] = held
        try:
            fault("flush_" + role)
            held.flush()
        except OSError:
            if role not in {"raw", "arrivals"}:
                raise
            warnings.add("raw_flush_failed")
        control_hash = None
        if role in {"manifest", "connections"}:
            controls[role] = held.read_control()
            control_hash = hashlib.sha256(controls[role]).hexdigest()
        artifacts.append(ClosedArtifact(held.identity, role, held.size, held.stamp, control_hash))
    require(set(controls) == {"manifest", "connections"}, "required capture controls missing")
    values = json.loads(controls["manifest"])
    require(values["session_id"] == intent.session_id and values["creator"] == intent.creator
            and values["room_id"] == result.room_id and values["output_path"] == intent.output_path
            and values["parts_directory"] == intent.parts_path
            and values["finalization"] == {"status": "pending", "error": None}
            and values["status"] in {"completed", "interrupted"} and values["error"] is None
            and values["interrupted"] == result.interrupted, "capture manifest binding conflicts")
    require(controls["connections"].endswith(b"\n"), "connection control closure incomplete")
    records = [json.loads(line) for line in controls["connections"].splitlines()]
    connection_records = [v for v in records if "connection" in v and "outcome" in v]
    expected_parts = tuple(sorted(result.parts, key=part_order))
    actual_parts = tuple(sorted((p for p in names if _role(p.name) == "flv"), key=part_order))
    require(expected_parts == actual_parts and values["part_count"] == len(actual_parts),
            "retained writer inventory conflicts")
    observed_parts = []
    for record in connection_records:
        number = record["connection"]
        timings = record["part_timings"]
        part_names = [timing["name"] for timing in timings]
        require(record["part_start"] == (part_names[0] if part_names else None)
                and record["part_end"] == (part_names[-1] if part_names else None),
                "connection part ranges conflict")
        observed_parts.extend(part_names)
        for key, suffix in (("raw_copy", "raw"), ("raw_arrivals", "arrivals.jsonl")):
            name = record[key]
            if name is not None:
                require(name == f"connection-{number:04d}.{suffix}" and name in handles,
                        "raw connection reference conflicts")
    expected_records = {v.number: v for v in result.connections}
    actual_numbers = [v["connection"] for v in connection_records]
    require(len(actual_numbers) == len(set(actual_numbers)) and actual_numbers == sorted(actual_numbers)
            and set(actual_numbers) <= set(expected_records), "connection history conflicts")
    for actual in connection_records:
        expected = expected_records[actual["connection"]]
        require(actual["raw_copy"] == (expected.raw_copy.name if expected.raw_copy else None)
                and actual["raw_arrivals"] == (expected.raw_arrivals.name if expected.raw_arrivals else None)
                and [v["name"] for v in actual["part_timings"]] ==
                    [v.path.name for v in expected.part_timings],
                "persisted connection differs from native capture evidence")
    require(observed_parts == [p.name for p in actual_parts]
            and connection_records and values["connection_count"] >= max(v["connection"] for v in connection_records),
            "connection inventory does not bind writer output")
    missing = [v for v in result.connections if v.number not in actual_numbers]
    omitted = _coalesced_recovery(records, intent.session_id)
    # LIVE deliberately omits repeated resolver-only records inside a durable
    # outage. Preserve that contract; missing media/raw attempts are never excused.
    require(len(missing) <= omitted and all(v.outcome == "resolver_error" and not v.parts
            and not v.part_timings and v.raw_copy is None and v.raw_arrivals is None for v in missing)
            and values["connection_count"] == max(expected_records),
            "connection history differs from closed capture")
    referenced = {v[key] for v in connection_records for key in ("raw_copy", "raw_arrivals") if v[key]}
    if any(a.role in {"raw", "arrivals"} and a.identity.components[-1] not in referenced for a in artifacts):
        require("raw_warning" in warnings, "unexplained raw diagnostic remainder")
        warnings.add("raw_remainder_retained")
    disposition = "assembly" if actual_parts else "empty"
    if disposition == "empty":
        require(source_items == 0 and not warnings
                and all(a.role != "raw" or a.size == 0 for a in artifacts),
                "empty capture has ambiguous retained source evidence")
    # Source order for FLV, then per-connection diagnostics, then the hashed controls.
    artifacts.sort(key=_inventory_order)
    seal = ClosureSeal(intent.session_id, generation, result.room_id, intent.raw_copy,
                       values["ended_at"], tuple(artifacts), tuple(sorted(warnings)), disposition)
    def verify():
        require(names == tuple(sorted((p for p in directory.iterdir()
                                      if p.name != "finalization-owner.json"), key=lambda p: p.name)),
                "capture inventory changed before handoff")
        parent.verify()
        for held in handles.values():
            held.verify()
    verify()
    return seal, verify
