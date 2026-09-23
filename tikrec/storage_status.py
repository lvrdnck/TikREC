"""Read-only storage status shared by automation admission and service health."""

from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any


GIB = 1024**3
DEFAULT_MINIMUM_FREE_SPACE_GIB = 10
MAX_MINIMUM_FREE_SPACE_GIB = 1024


class StorageStatus:
    """Inspect available space without creating directories or exposing local paths."""

    def __init__(self, output_directory: Path | None,
                 minimum_free_space_gib: int = DEFAULT_MINIMUM_FREE_SPACE_GIB,
                 *, disk_usage: Callable[[Path], Any] = shutil.disk_usage) -> None:
        if (type(minimum_free_space_gib) is not int
                or not 1 <= minimum_free_space_gib <= MAX_MINIMUM_FREE_SPACE_GIB):
            raise ValueError("minimum free space must be an integer from 1 to 1024 GiB")
        self.output_directory = output_directory
        self.minimum_free_bytes = minimum_free_space_gib * GIB
        self.warning_free_bytes = max(20 * GIB, 2 * self.minimum_free_bytes)
        self._disk_usage = disk_usage

    def snapshot(self) -> dict:
        """Return a bounded status using the nearest existing storage parent."""
        result = {
            "state": "unconfigured", "free_bytes": None,
            "minimum_free_bytes": self.minimum_free_bytes,
            "warning_free_bytes": self.warning_free_bytes,
        }
        if self.output_directory is None:
            return result
        try:
            parent = nearest_existing_directory(self.output_directory)
            free = self._disk_usage(parent).free
        except Exception:
            result["state"] = "unavailable"
            return result
        if type(free) is not int or free < 0:
            result["state"] = "unavailable"
            return result
        result["free_bytes"] = free
        result["state"] = (
            "blocked" if free < self.minimum_free_bytes else
            "warning" if free < self.warning_free_bytes else "ok"
        )
        return result


def nearest_existing_directory(directory: Path) -> Path:
    """Find a disk-usage target without creating the configured output path."""
    candidate = directory
    while True:
        try:
            candidate.lstat()
        except FileNotFoundError:
            parent = candidate.parent
            if parent == candidate:
                raise OSError("no existing storage parent")
            candidate = parent
            continue
        except OSError:
            raise OSError("storage parent is unavailable") from None
        if not candidate.is_dir():
            raise OSError("storage parent is not a directory")
        return candidate
