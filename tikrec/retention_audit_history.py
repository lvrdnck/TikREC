"""Validate durable retention events as coherent, possibly incomplete operations."""

from __future__ import annotations

import math
import os
import re
import stat
import uuid
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath


_COMMON = {"schema_version", "event", "operation_id"}
_HASH = re.compile(r"[0-9a-f]{64}\Z")
_ARTIFACT = {"relative_path", "kind", "mode", "size", "device", "inode",
             "mtime_ns", "ctime_ns", "link_count", "attributes", "volume"}
_INTENT = {"timestamp", "root", "session_id", "creator", "ended_at",
           "max_age_days", "protected", "protected_creators", "artifacts", "order"}


@dataclass
class _Operation:
    order: tuple[str, ...]
    index: int = 0
    pending: str | None = None
    last_deleted: str | None = None
    terminal: bool = False


class AuditHistory:
    """Accept only one ordered deletion protocol for each unique operation ID."""

    def __init__(self, root: Path) -> None:
        self.root = os.path.normcase(os.path.abspath(root))
        self.operations: dict[str, _Operation] = {}
        self.latest: str | None = None

    def accept(self, record: object) -> None:
        """Check one schema-1 event without consulting possibly deleted media."""
        if (type(record) is not dict or type(record.get("schema_version")) is not int
                or record["schema_version"] != 1
                or type(record.get("event")) is not str
                or not _uuid(record.get("operation_id"))):
            raise ValueError("invalid retention audit record")
        event, operation_id = record["event"], record["operation_id"]
        if event == "intent":
            if operation_id in self.operations:
                raise ValueError("duplicate retention audit intent")
            self.operations[operation_id] = _Operation(_intent_order(record, self.root))
            self.latest = operation_id
            return
        operation = self.operations.get(operation_id)
        # A later intent freezes every older crash tail; deletion never resumes it.
        if operation is None or operation.terminal or operation_id != self.latest:
            raise ValueError("orphan or terminal retention audit event")
        if event == "completed":
            _fields(record, _COMMON | {"deleted_count"})
            if (type(record["deleted_count"]) is not int
                    or record["deleted_count"] != len(operation.order)
                    or operation.index != len(operation.order)
                    or operation.pending is not None):
                raise ValueError("incomplete retention audit completion")
            operation.terminal = True
            return
        if event not in {"attempt", "deleted", "failed"}:
            raise ValueError("invalid retention audit event")
        _fields(record, _COMMON | {"path"} |
                ({"error_type"} if event == "failed" else set()))
        if event == "failed":
            # A completed deleted line can precede a failed fsync of that same
            # line; the executor then records failed for the just-removed path.
            current = (operation.index < len(operation.order)
                       and record["path"] == operation.order[operation.index]
                       and operation.pending in {None, record["path"]})
            after_deleted = (operation.pending is None
                             and operation.last_deleted == record["path"])
            if (not (current or after_deleted)
                    or type(record["error_type"]) is not str
                    or not record["error_type"]):
                raise ValueError("invalid retention audit failure")
            operation.terminal = True
            return
        if (operation.index >= len(operation.order)
                or record["path"] != operation.order[operation.index]):
            raise ValueError("retention audit artifact order changed")
        if event == "attempt":
            if operation.pending is not None:
                raise ValueError("duplicate retention audit attempt")
            operation.pending = record["path"]
            operation.last_deleted = None
        else:
            if operation.pending != record["path"]:
                raise ValueError("retention audit deletion lacks attempt")
            operation.index += 1
            operation.pending = None
            operation.last_deleted = record["path"]


def _intent_order(record: dict, journal_root: str) -> tuple[str, ...]:
    _fields(record, _COMMON | _INTENT,
            {"target_controls", "recovery_byte_hashes"})
    if (not _finite(record["timestamp"]) or not _finite(record["ended_at"])
            or not _absolute(record["root"]) or not _uuid(record["session_id"])
            or type(record["creator"]) is not str or not record["creator"]
            or type(record["max_age_days"]) is not int
            or not 1 <= record["max_age_days"] <= 3650
            or record["protected"] is not False
            or type(record["protected_creators"]) is not list
            or any(type(value) is not str or not value
                   for value in record["protected_creators"])):
        raise ValueError("invalid retention audit intent")
    root = record["root"]
    # The journal is keyed by the lexical no-redirect root used by the executor.
    # Reject foreign paths and noncanonical aliases without opening deleted media.
    if (not os.path.isabs(root) or os.path.normcase(root) != journal_root
            or os.path.normcase(os.path.abspath(root)) != os.path.normcase(root)):
        raise ValueError("retention audit intent names another root")
    order, artifacts = record["order"], record["artifacts"]
    if (type(order) is not list or not order or type(artifacts) is not list
            or len(order) != len(artifacts)
            or any(not _relative(path) for path in order)
            or len(set(order)) != len(order)):
        raise ValueError("invalid retention audit artifact order")
    for path, artifact in zip(order, artifacts):
        _artifact(artifact, path)
    if len({tuple(sorted(item["volume"].items())) for item in artifacts}) != 1:
        raise ValueError("retention audit artifacts cross volumes")
    media_order = _destructive_order(order, artifacts, record["session_id"])
    for field in ("target_controls", "recovery_byte_hashes"):
        if field in record:
            hashes = record[field]
            if (type(hashes) is not dict or any(
                    type(name) is not str or not name or not _digest(value)
                    for name, value in hashes.items())):
                raise ValueError("invalid retention audit byte proof")
            if field == "target_controls" and ("session.json" not in hashes or not
                    set(hashes).issubset({"session.json", "connections.jsonl"})):
                raise ValueError("unknown retention audit control")
            if field == "recovery_byte_hashes" and not set(hashes).issubset(media_order):
                raise ValueError("retention audit byte proof is outside order")
    return tuple(order)


def _destructive_order(order: list[str], artifacts: list[dict],
                       session_id: str) -> tuple[str, ...]:
    """Require one-session deletion order and return its retained-media paths."""
    if len(order) < 4:
        raise ValueError("retention audit omits required artifacts")
    parts_name, output_name = order[-2:]
    parts = Path(parts_name)
    if (parts.name != parts_name or not parts_name.lower().endswith(".parts")
            or Path(output_name).name != output_name
            or output_name != parts.with_suffix(".mp4").name
            or order[-3] != str(parts / "session.json")
            or artifacts[-2]["kind"] != "directory"
            or any(item["kind"] != "file" for item in (*artifacts[:-2], artifacts[-1]))):
        raise ValueError("invalid retention audit destructive order")
    children = list(order[:-3])
    if children and children[-1] == str(parts / "connections.jsonl"):
        children.pop()
    names = []
    for path in children:
        child = Path(path)
        if child.parent != parts or str(child) != path:
            raise ValueError("retention audit child is outside its parts directory")
        names.append(child.name)
    evidence = re.compile(rf"\.tikrec-writer-crash-{re.escape(session_id)}"
                          rf"-part-[0-9]{{4,}}\.evidence\Z")
    if (names != sorted(set(names))
            or not any(re.fullmatch(r"part-[0-9]+\.flv", name) for name in names)
            or any(re.fullmatch(r"part-[0-9]+\.flv", name) is None
                   and evidence.fullmatch(name) is None for name in names)):
        raise ValueError("invalid retention audit retained-media order")
    return tuple(children)


def _artifact(artifact: object, path: str) -> None:
    if type(artifact) is not dict or set(artifact) != _ARTIFACT:
        raise ValueError("invalid retention audit artifact")
    volume = artifact["volume"]
    if (artifact["relative_path"] != path or artifact["kind"] not in {"file", "directory"}
            or (not stat.S_ISDIR(artifact["mode"]) if artifact["kind"] == "directory"
                else not stat.S_ISREG(artifact["mode"]))
            or artifact["kind"] == "file" and artifact["link_count"] != 1
            or any(type(artifact[name]) is not int or artifact[name] < 0 for name in
                   ("mode", "size", "device", "inode", "mtime_ns", "ctime_ns",
                    "link_count", "attributes"))
            or type(volume) is not dict or set(volume) != {"platform", "point", "identity"}
            or any(type(value) is not str for value in volume.values())):
        raise ValueError("invalid retention audit artifact")


def _fields(record: dict, required: set[str], optional: set[str] = frozenset()) -> None:
    if not required.issubset(record) or not set(record).issubset(required | optional):
        raise ValueError("invalid retention audit event fields")


def _uuid(value: object) -> bool:
    try:
        return type(value) is str and str(uuid.UUID(value)) == value
    except (ValueError, AttributeError):
        return False


def _finite(value: object) -> bool:
    return type(value) in {int, float} and math.isfinite(value)


def _digest(value: object) -> bool:
    return type(value) is str and _HASH.fullmatch(value) is not None


def _absolute(value: object) -> bool:
    return (type(value) is str and bool(value) and "\x00" not in value and
            (PureWindowsPath(value).is_absolute() or PurePosixPath(value).is_absolute()))


def _relative(value: object) -> bool:
    if type(value) is not str or value in {"", "."} or "\x00" in value:
        return False
    windows, posix = PureWindowsPath(value), PurePosixPath(value)
    return (not windows.drive and not windows.root and not posix.root
            and ".." not in windows.parts and ".." not in posix.parts)
