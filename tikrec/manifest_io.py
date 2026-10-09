"""Atomic manifest publication with optional recovery ownership conditions."""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Callable
from pathlib import Path
from .capture_writer_owners import open_capture_file


def write_manifest(path: Path, values: dict, *, expected_digest: str | None = None,
                   guard: Callable[[], None] | None = None) -> None:
    """Replace one manifest only while its inspected owner remains current."""
    temporary = path.with_name(f".{path.name}.partial")
    try:
        with open_capture_file(temporary, "w", encoding="utf-8") as handle:
            json.dump(values, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        if (expected_digest is not None and hashlib.sha256(
                path.read_bytes()).hexdigest() != expected_digest):
            raise ValueError("manifest changed before conditional recovery commit")
        if guard is not None:
            guard()
        os.replace(temporary, path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
