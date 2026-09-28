"""Durable external journal for one bounded retention operation."""

from __future__ import annotations

import hashlib
import json
import os
import stat
from collections.abc import Callable
from pathlib import Path

from .service_job import default_job_state_path
from .retention_audit_history import AuditHistory


AUDIT_SCHEMA = 1
_MAX_RECORD_BYTES = 64 * 1024 * 1024
_POSIX_SYNC = os.name != "nt"


def default_audit_path(root: Path) -> Path:
    """Keep each recording root's append-only history in user state storage."""
    digest = hashlib.sha256(os.fsencode(root)).hexdigest()
    return default_job_state_path().parent / "retention-audit" / f"{digest}.jsonl"


class RetentionAudit:
    """Append and sync every event without placing an audit artifact in the root."""

    def __init__(self, root: Path, path: Path | None = None) -> None:
        self.root = Path(root)
        self.path = Path(path) if path is not None else default_audit_path(root)
        root_abs, path_abs = Path(os.path.abspath(root)), Path(os.path.abspath(self.path))
        # Resolve existing aliases as well as lexical children of the recording root.
        if (root_abs == path_abs or root_abs in path_abs.parents
                or root_abs.resolve() == path_abs.resolve()
                or root_abs.resolve() in path_abs.resolve().parents):
            raise ValueError("retention audit must be outside recording root")
        self.handle = None
        self.identity = None

    def __enter__(self) -> RetentionAudit:
        _prepare_parent(self.path.parent)
        # A parent redirect inserted after construction must not place the journal
        # among the artifacts being deleted.
        if (self.root.resolve() == self.path.resolve()
                or self.root.resolve() in self.path.resolve().parents):
            raise ValueError("retention audit must be outside recording root")
        flags = os.O_RDWR | os.O_APPEND | getattr(os, "O_BINARY", 0)
        flags |= getattr(os, "O_NOFOLLOW", 0)
        try:
            descriptor = os.open(self.path, flags | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            descriptor = os.open(self.path, flags)
        try:
            opened, named = os.fstat(descriptor), self.path.lstat()
            if (not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1
                    or not stat.S_ISREG(named.st_mode) or named.st_nlink != 1
                    or (opened.st_dev, opened.st_ino) != (named.st_dev, named.st_ino)
                    or getattr(named, "st_file_attributes", 0) & 0x400):
                raise ValueError("retention audit journal is redirected or multiply linked")
            self.identity = (opened.st_dev, opened.st_ino)
            self.handle = os.fdopen(descriptor, "r+b", buffering=0)
            # A prior torn write must never be joined to a new deletion intent.
            _validate_history(self.handle, self.root)
            if _POSIX_SYNC:
                # Retry must also publish an entry left visible by a failed sync.
                _sync_directory(self.path.parent)
            return self
        except BaseException:
            if self.handle is not None:
                self.handle.close()
            else:
                os.close(descriptor)
            raise

    def __exit__(self, *_exc) -> None:
        self.handle.close()

    def append(self, event: str, operation_id: str, *,
               before_sync: Callable[[], None] | None = None,
               after_sync: Callable[[], None] | None = None, **fields) -> None:
        """Persist one event and publish the sync boundary to its caller."""
        named = self.path.lstat()
        if ((named.st_dev, named.st_ino) != self.identity
                or named.st_nlink != 1 or not stat.S_ISREG(named.st_mode)
                or getattr(named, "st_file_attributes", 0) & 0x400):
            raise ValueError("retention audit journal changed")
        payload = {"schema_version": AUDIT_SCHEMA, "event": event,
                   "operation_id": operation_id, **fields}
        data = (json.dumps(payload, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")
        written = self.handle.write(data)
        if written != len(data):
            raise OSError("short retention audit write")
        if before_sync is not None:
            # A fault inside fsync may follow successful persistence but precede
            # the after-sync callback, so the caller must retain uncertainty.
            before_sync()
        os.fsync(self.handle.fileno())
        if after_sync is not None:
            # The executor must publish known durability before append returns
            # so a later interrupt cannot be mistaken for a pre-intent refusal.
            after_sync()


def _prepare_parent(parent: Path) -> None:
    """Create each missing audit ancestor and durably publish its directory entry."""
    missing = []
    current = parent
    while not current.exists():
        missing.append(current)
        if current.parent == current:
            raise ValueError("retention audit parent is unavailable")
        current = current.parent
    if not current.is_dir():
        raise ValueError("retention audit parent is not a directory")
    missing_set = set(missing)
    # Publish each entry before creating its child. Re-sync existing entries too:
    # a prior failed attempt may have left one visible but not durable.
    for directory in (*reversed(parent.parents), parent):
        if directory.parent == directory:
            continue
        if directory in missing_set:
            directory.mkdir()
        if _POSIX_SYNC:
            _sync_directory(directory.parent)


def _sync_directory(directory: Path) -> None:
    """Flush one POSIX directory entry boundary after creation."""
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(directory, flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _validate_history(handle, root: Path) -> None:
    """Require complete, coherent schema-1 operations before another intent."""
    handle.seek(0)
    history = AuditHistory(root)
    try:
        while record_bytes := handle.readline(_MAX_RECORD_BYTES + 1):
            if len(record_bytes) > _MAX_RECORD_BYTES or not record_bytes.endswith(b"\n"):
                raise ValueError("incomplete retention audit record")
            record = json.loads(record_bytes.decode("utf-8"), object_pairs_hook=_unique_fields)
            history.accept(record)
    except (UnicodeError, ValueError, TypeError) as error:
        raise ValueError("retention audit journal is incomplete or invalid") from error
    handle.seek(0, os.SEEK_END)


def _unique_fields(pairs: list[tuple[str, object]]) -> dict:
    """Reject conflicting JSON fields rather than accepting the last value."""
    values = {}
    for name, value in pairs:
        if name in values:
            raise ValueError("duplicate retention audit field")
        values[name] = value
    return values
