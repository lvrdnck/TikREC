"""Durable config publication sharing retention's final mutation authority."""

import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from .policy_lock import policy_lock


def write_document(path: Path, document: dict) -> None:
    """Prepare a complete replacement, then serialize only its committed update."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                prefix=f".{path.name}.", suffix=".partial",
                                delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(document, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        # The temporary is closed for Windows promotion; readers remain unlocked.
        with policy_lock(path, "write") as lease:
            lease.assert_held()
            os.replace(temporary, path)
            if os.name != "nt":
                descriptor = os.open(path.parent, os.O_RDONLY)
                try:
                    os.fsync(descriptor)
                finally:
                    os.close(descriptor)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
