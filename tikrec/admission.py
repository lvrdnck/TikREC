"""Non-mutating unattended-recording admission and storage checks."""

from __future__ import annotations

import shutil
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from .output_naming import OutputNameUnavailableError, monitored_recording_paths


MINIMUM_FREE_BYTES = 10 * 1024**3


class RecordingAdmission:
    """Evaluate whether detected creators could use the existing recording slot."""

    def __init__(
        self,
        output_directory: Path | None,
        controller_health: Callable[[], dict],
        *,
        clock: Callable[[], datetime] = datetime.now,
        disk_usage: Callable[[Path], Any] = shutil.disk_usage,
        allocator: Callable[..., tuple[Path, Path]] = monitored_recording_paths,
    ) -> None:
        self._output_directory = output_directory
        self._controller_health = controller_health
        self._clock = clock
        self._disk_usage = disk_usage
        self._allocator = allocator

    def evaluate(self, monitoring: dict) -> dict:
        """Return a fresh monitoring snapshot enriched with current admission state."""
        observations = [dict(item) for item in monitoring.get("creators", [])]
        live = any(item.get("state") == "live" for item in observations)
        slot_available = self._slot_available() if live else False
        free_bytes: int | None = None
        storage_available = False
        if live and slot_available and self._output_directory is not None:
            free_bytes = self._free_bytes()
            storage_available = free_bytes is not None
        moment = (
            self._moment()
            if (storage_available and free_bytes is not None
                and free_bytes >= MINIMUM_FREE_BYTES)
            else None
        )
        for item in observations:
            item["admission"] = self._admission(
                item, slot_available, storage_available, free_bytes, moment
            )
        snapshot = dict(monitoring)
        snapshot["minimum_free_bytes"] = MINIMUM_FREE_BYTES
        snapshot["creators"] = observations
        return snapshot

    def _admission(
        self,
        observation: dict,
        slot_available: bool,
        storage_available: bool,
        free_bytes: int | None,
        moment: datetime | None,
    ) -> dict:
        if observation.get("state") != "live":
            return _result("not_applicable")
        if not slot_available:
            return _result("skipped", "recording_slot_unavailable")
        if self._output_directory is None:
            return _result("blocked", "output_directory_unconfigured")
        if not storage_available or free_bytes is None:
            return _result("blocked", "storage_unavailable")
        if free_bytes < MINIMUM_FREE_BYTES:
            return _result("blocked", "low_free_space", free_bytes=free_bytes)
        if moment is None:
            return _result(
                "blocked", "storage_unavailable", free_bytes=free_bytes
            )
        try:
            output, parts = self._allocator(
                self._output_directory, observation["creator"], moment=moment
            )
        except OutputNameUnavailableError:
            return _result(
                "blocked", "output_name_unavailable", free_bytes=free_bytes
            )
        except Exception:
            # Candidate inspection is advisory; fixed output prevents leaking details.
            return _result("blocked", "storage_unavailable", free_bytes=free_bytes)
        return _result(
            "ready", free_bytes=free_bytes, output_path=output, parts_path=parts
        )

    def _slot_available(self) -> bool:
        try:
            health = self._controller_health()
        except Exception:
            return False
        return isinstance(health, dict) and health.get("available") is True

    def _free_bytes(self) -> int | None:
        try:
            parent = _nearest_existing_directory(self._output_directory)
            free = self._disk_usage(parent).free
        except Exception:
            return None
        return free if type(free) is int and free >= 0 else None

    def _moment(self) -> datetime | None:
        try:
            moment = self._clock()
        except Exception:
            return None
        return moment if isinstance(moment, datetime) else None


def _nearest_existing_directory(directory: Path | None) -> Path:
    if directory is None:
        raise OSError("output directory is unconfigured")
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


def _result(
    state: str,
    reason: str | None = None,
    *,
    free_bytes: int | None = None,
    output_path: Path | None = None,
    parts_path: Path | None = None,
) -> dict:
    return {
        "state": state,
        "reason": reason,
        "free_bytes": free_bytes,
        "output_path": None if output_path is None else str(output_path),
        "parts_directory": None if parts_path is None else str(parts_path),
    }
