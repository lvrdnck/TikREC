"""Non-mutating unattended-recording admission and storage checks."""

from __future__ import annotations

import shutil
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from .output_naming import OutputNameUnavailableError, monitored_recording_paths
from .storage_status import DEFAULT_MINIMUM_FREE_SPACE_GIB, GIB, StorageStatus


MINIMUM_FREE_BYTES = DEFAULT_MINIMUM_FREE_SPACE_GIB * GIB


class RecordingAdmission:
    """Evaluate whether detected creators could use current recording capacity."""

    def __init__(
        self,
        output_directory: Path | None,
        controller_health: Callable[[], dict],
        *,
        clock: Callable[[], datetime] = datetime.now,
        disk_usage: Callable[[Path], Any] = shutil.disk_usage,
        allocator: Callable[..., tuple[Path, Path]] = monitored_recording_paths,
        storage_status: StorageStatus | None = None,
    ) -> None:
        self._output_directory = output_directory
        self._controller_health = controller_health
        self._clock = clock
        self.storage_status = storage_status or StorageStatus(output_directory, disk_usage=disk_usage)
        self._allocator = allocator

    def evaluate(self, monitoring: dict) -> dict:
        """Return a fresh monitoring snapshot enriched with current admission state."""
        observations = [dict(item) for item in monitoring.get("creators", [])]
        live = any(item.get("state") == "live" for item in observations)
        slot_available = self._slot_available() if live else False
        storage = (self.storage_status.snapshot() if live and slot_available else None)
        free_bytes = storage["free_bytes"] if storage is not None else None
        storage_available = storage is not None and storage["state"] in {"ok", "warning", "blocked"}
        moment = (
            self._moment()
            if storage_available and free_bytes is not None
            and free_bytes >= self.storage_status.minimum_free_bytes
            else None
        )
        for item in observations:
            item["admission"] = self._admission(
                item, slot_available, storage_available, free_bytes, moment
            )
        snapshot = dict(monitoring)
        snapshot["minimum_free_bytes"] = self.storage_status.minimum_free_bytes
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
        if free_bytes < self.storage_status.minimum_free_bytes:
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

    def _moment(self) -> datetime | None:
        try:
            moment = self._clock()
        except Exception:
            return None
        return moment if isinstance(moment, datetime) else None


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
