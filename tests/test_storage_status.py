"""Offline storage policy states and admission use of the same threshold."""

from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from tikrec.admission import RecordingAdmission
from tikrec.storage_status import GIB, StorageStatus


@pytest.mark.parametrize("minimum,free,state,warning", [
    (10, 10 * GIB - 1, "blocked", 20 * GIB),
    (10, 10 * GIB, "warning", 20 * GIB),
    (10, 20 * GIB, "ok", 20 * GIB),
    (15, 29 * GIB, "warning", 30 * GIB),
    (15, 30 * GIB, "ok", 30 * GIB),
])
def test_storage_threshold_states(tmp_path: Path, minimum: int, free: int,
                                  state: str, warning: int) -> None:
    policy = StorageStatus(tmp_path, minimum, disk_usage=lambda _: SimpleNamespace(free=free))
    assert policy.snapshot() == {
        "state": state, "free_bytes": free,
        "minimum_free_bytes": minimum * GIB, "warning_free_bytes": warning,
    }


def test_unconfigured_and_unavailable_status_hide_paths(tmp_path: Path) -> None:
    assert StorageStatus(None).snapshot()["state"] == "unconfigured"
    def unavailable(_):
        raise OSError(f"secret path: {tmp_path}")
    snapshot = StorageStatus(tmp_path, disk_usage=unavailable).snapshot()
    assert snapshot["state"] == "unavailable"
    assert str(tmp_path) not in str(snapshot)


@pytest.mark.parametrize("free,reason", [
    (14 * GIB, "low_free_space"), (15 * GIB, None), (29 * GIB, None),
])
def test_custom_reserve_controls_automatic_admission(tmp_path: Path, free: int,
                                                     reason: str | None) -> None:
    policy = StorageStatus(tmp_path, 15, disk_usage=lambda _: SimpleNamespace(free=free))
    admission = RecordingAdmission(tmp_path, lambda: {"available": True},
                                   storage_status=policy,
                                   clock=lambda: datetime(2026, 9, 23))
    result = admission.evaluate({"creators": [{"creator": "alpha", "state": "live"}]})
    assert result["minimum_free_bytes"] == 15 * GIB
    assert result["creators"][0]["admission"]["reason"] == reason
