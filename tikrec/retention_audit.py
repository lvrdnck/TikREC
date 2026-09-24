"""Durable external journal for one bounded retention operation."""

from __future__ import annotations

import hashlib
import json
import os
import stat
from pathlib import Path

from .service_job import default_job_state_path


AUDIT_SCHEMA = 1


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
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # A parent redirect inserted after construction must not place the journal
        # among the artifacts being deleted.
        if (self.root.resolve() == self.path.resolve()
                or self.root.resolve() in self.path.resolve().parents):
            raise ValueError("retention audit must be outside recording root")
        flags = os.O_WRONLY | os.O_APPEND | getattr(os, "O_BINARY", 0)
        flags |= getattr(os, "O_NOFOLLOW", 0)
        created = False
        try:
            descriptor = os.open(self.path, flags | os.O_CREAT | os.O_EXCL, 0o600)
            created = True
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
            self.handle = os.fdopen(descriptor, "wb", buffering=0)
            if created and os.name != "nt":
                parent = os.open(self.path.parent, os.O_RDONLY)
                try:
                    os.fsync(parent)
                finally:
                    os.close(parent)
            return self
        except BaseException:
            if self.handle is not None:
                self.handle.close()
            else:
                os.close(descriptor)
            raise

    def __exit__(self, *_exc) -> None:
        self.handle.close()

    def append(self, event: str, operation_id: str, **fields) -> None:
        """Persist one schema-versioned event before returning to the caller."""
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
        os.fsync(self.handle.fileno())
