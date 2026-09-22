"""Offline tests for non-mutating unattended-recording admission."""

import json
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from tikrec.admission import MINIMUM_FREE_BYTES, RecordingAdmission
from tikrec.capture import CaptureResult
from tikrec.output_naming import OutputPathInspectionError
from tikrec.recording import RecordingController


MOMENT = datetime(2026, 9, 22, 14, 30, 15)


def _monitoring(*states: str) -> dict:
    return {
        "poll_interval_seconds": 30.0,
        "creators": [
            {
                "creator": f"creator{index}",
                "state": state,
                "observed_at": 1.0,
                "room_id": str(100 + index) if state == "live" else None,
                "unknown_reason": None,
            }
            for index, state in enumerate(states, 1)
        ],
    }


def _admission(
    directory: Path | None,
    *,
    available: bool = True,
    free: int = MINIMUM_FREE_BYTES,
    disk_usage=None,
    allocator=None,
) -> RecordingAdmission:
    options = {
        "clock": lambda: MOMENT,
        "disk_usage": disk_usage or (lambda _: SimpleNamespace(free=free)),
    }
    if allocator is not None:
        options["allocator"] = allocator
    return RecordingAdmission(
        directory, lambda: {"available": available}, **options
    )


def test_missing_output_directory_blocks_live_without_stopping_detection():
    snapshot = _admission(None).evaluate(_monitoring("live"))
    assert snapshot["minimum_free_bytes"] == 10 * 1024**3
    assert snapshot["creators"][0]["state"] == "live"
    assert snapshot["creators"][0]["admission"] == {
        "state": "blocked",
        "reason": "output_directory_unconfigured",
        "free_bytes": None,
        "output_path": None,
        "parts_directory": None,
    }


@pytest.mark.parametrize("create_directory", [True, False])
def test_existing_or_future_directory_uses_nearest_storage_without_creation(
    tmp_path: Path, create_directory: bool
):
    directory = tmp_path / "future" / "recordings"
    if create_directory:
        directory.mkdir(parents=True)
    inspected = []
    evaluator = _admission(
        directory,
        disk_usage=lambda path: inspected.append(path) or SimpleNamespace(
            free=MINIMUM_FREE_BYTES
        ),
    )
    snapshot = evaluator.evaluate(_monitoring("live"))
    result = snapshot["creators"][0]["admission"]
    assert result["state"] == "ready"
    assert Path(result["output_path"]).name == "creator1-20260922-143015.mp4"
    assert Path(result["parts_directory"]).name == "creator1-20260922-143015.parts"
    assert inspected == [directory if create_directory else tmp_path]
    assert directory.exists() is create_directory


@pytest.mark.parametrize(
    "free,state,reason",
    [
        (MINIMUM_FREE_BYTES, "ready", None),
        (MINIMUM_FREE_BYTES - 1, "blocked", "low_free_space"),
    ],
)
def test_free_space_floor_is_inclusive(tmp_path: Path, free: int, state: str, reason):
    result = _admission(tmp_path, free=free).evaluate(_monitoring("live"))
    admission = result["creators"][0]["admission"]
    assert (admission["state"], admission["reason"], admission["free_bytes"]) == (
        state, reason, free,
    )


@pytest.mark.parametrize(
    "disk_usage",
    [
        lambda _: (_ for _ in ()).throw(OSError("secret storage failure")),
        lambda _: SimpleNamespace(free=-1),
        lambda _: SimpleNamespace(free=True),
        lambda _: object(),
    ],
)
def test_storage_inspection_failures_are_sanitized(tmp_path: Path, disk_usage):
    result = _admission(tmp_path, disk_usage=disk_usage).evaluate(_monitoring("live"))
    assert result["creators"][0]["admission"]["reason"] == "storage_unavailable"
    assert "secret" not in json.dumps(result)


def test_storage_parent_stat_failure_is_sanitized(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    directory = tmp_path / "blocked"
    original = Path.lstat

    def fail_selected(path: Path):
        if path == directory:
            raise PermissionError("secret stat failure")
        return original(path)

    monkeypatch.setattr(Path, "lstat", fail_selected)
    result = _admission(
        directory,
        disk_usage=lambda _: pytest.fail("stat failure must stop capacity check"),
    ).evaluate(_monitoring("live"))
    assert result["creators"][0]["admission"]["reason"] == "storage_unavailable"
    assert "secret" not in json.dumps(result)


def test_clock_failure_is_storage_unavailable_and_sanitized(tmp_path: Path):
    def fail():
        raise RuntimeError("secret clock failure")

    evaluator = RecordingAdmission(
        tmp_path, lambda: {"available": True}, clock=fail,
        disk_usage=lambda _: SimpleNamespace(free=MINIMUM_FREE_BYTES),
    )
    result = evaluator.evaluate(_monitoring("live"))
    assert result["creators"][0]["admission"]["reason"] == "storage_unavailable"
    assert "secret" not in json.dumps(result)


def test_output_and_parts_collisions_select_deterministic_suffix(tmp_path: Path):
    (tmp_path / "creator1-20260922-143015.mp4").write_bytes(b"keep")
    (tmp_path / "creator1-20260922-143015-2.parts").mkdir()
    result = _admission(tmp_path).evaluate(_monitoring("live"))
    admission = result["creators"][0]["admission"]
    assert Path(admission["output_path"]).name == "creator1-20260922-143015-3.mp4"
    assert Path(admission["parts_directory"]).name == "creator1-20260922-143015-3.parts"


def test_collision_search_is_bounded_and_preserves_artifacts(tmp_path: Path, monkeypatch):
    import tikrec.output_naming as naming

    original = {}
    for suffix in ("", "-2"):
        path = tmp_path / f"creator1-20260922-143015{suffix}.mp4"
        path.write_bytes(suffix.encode() or b"first")
        original[path] = path.read_bytes()
    monkeypatch.setattr(naming, "_MAX_COLLISION_INDEX", 2)
    result = _admission(tmp_path).evaluate(_monitoring("live"))
    admission = result["creators"][0]["admission"]
    assert admission["reason"] == "output_name_unavailable"
    assert all(path.read_bytes() == content for path, content in original.items())


def test_admission_creates_no_candidate_or_reservation_artifacts(tmp_path: Path):
    before = tuple(tmp_path.iterdir())
    monitoring = _monitoring("live")
    result = _admission(tmp_path).evaluate(monitoring)
    assert result is not monitoring and result["creators"] is not monitoring["creators"]
    assert tuple(tmp_path.iterdir()) == before
    assert not Path(result["creators"][0]["admission"]["output_path"]).exists()


@pytest.mark.parametrize(
    "health",
    [
        {"available": False, "active": True},
        {"available": False, "recovery_state": "reconciling"},
        {"available": False, "recovery_state": "failed"},
        {"available": False, "shutting_down": True},
        {},
    ],
)
def test_every_unavailable_controller_state_skips_without_storage(tmp_path: Path, health):
    evaluator = RecordingAdmission(
        tmp_path,
        lambda: health,
        disk_usage=lambda _: pytest.fail("busy admission must not inspect storage"),
    )
    admission = evaluator.evaluate(_monitoring("live"))["creators"][0]["admission"]
    assert (admission["state"], admission["reason"]) == (
        "skipped", "recording_slot_unavailable",
    )


def test_later_evaluation_becomes_ready_when_slot_is_available(tmp_path: Path):
    health = {"available": False}
    evaluator = RecordingAdmission(
        tmp_path, lambda: health, clock=lambda: MOMENT,
        disk_usage=lambda _: SimpleNamespace(free=MINIMUM_FREE_BYTES),
    )
    first = evaluator.evaluate(_monitoring("live"))["creators"][0]["admission"]
    health["available"] = True
    second = evaluator.evaluate(_monitoring("live"))["creators"][0]["admission"]
    assert first["state"] == "skipped" and second["state"] == "ready"


def test_non_live_states_are_not_applicable_and_skip_all_checks(tmp_path: Path):
    evaluator = RecordingAdmission(
        tmp_path,
        lambda: pytest.fail("non-live observations must not inspect the slot"),
        disk_usage=lambda _: pytest.fail("non-live observations must not inspect storage"),
    )
    result = evaluator.evaluate(_monitoring("pending", "offline", "unknown"))
    assert [item["admission"]["state"] for item in result["creators"]] == [
        "not_applicable", "not_applicable", "not_applicable",
    ]


def test_multiple_live_creators_are_evaluated_without_selecting_or_starting(tmp_path: Path):
    class Controller:
        def health(self):
            return {"available": True}

        def start(self, *_):
            pytest.fail("admission must not start a recording")

    controller = Controller()
    evaluator = RecordingAdmission(
        tmp_path, controller.health, clock=lambda: MOMENT,
        disk_usage=lambda _: SimpleNamespace(free=MINIMUM_FREE_BYTES),
    )
    result = evaluator.evaluate(_monitoring("live", "live"))
    admissions = [item["admission"] for item in result["creators"]]
    assert [item["state"] for item in admissions] == ["ready", "ready"]
    assert admissions[0]["output_path"] != admissions[1]["output_path"]


def test_path_inspection_failure_is_fixed_and_safe(tmp_path: Path):
    def fail(*_, **__):
        raise OutputPathInspectionError("https://cdn.test/a.flv?secret=hidden")

    result = _admission(tmp_path, allocator=fail).evaluate(_monitoring("live"))
    admission = result["creators"][0]["admission"]
    assert admission["reason"] == "storage_unavailable"
    assert admission["free_bytes"] == MINIMUM_FREE_BYTES
    assert "secret" not in json.dumps(result)


def test_active_manual_recording_owns_slot(tmp_path: Path):
    from threading import Event

    entered = Event()
    release = Event()

    def capture(url, **kwargs):
        entered.set()
        assert release.wait(2)
        return CaptureResult((), None)

    controller = RecordingController(capture=capture)
    try:
        controller.start(
            "https://www.tiktok.com/@manual/live", str(tmp_path / "manual.mp4")
        )
        assert entered.wait(2)
        evaluator = RecordingAdmission(
            tmp_path, controller.health,
            disk_usage=lambda _: pytest.fail("busy admission must skip storage"),
        )
        admission = evaluator.evaluate(_monitoring("live"))["creators"][0][
            "admission"
        ]
        assert (admission["state"], admission["reason"]) == (
            "skipped", "recording_slot_unavailable",
        )
    finally:
        release.set()
        controller.shutdown()


def test_low_automatic_space_never_changes_manual_start(tmp_path: Path):
    controller = RecordingController(
        capture=lambda url, **kwargs: CaptureResult((), None)
    )
    evaluator = RecordingAdmission(
        tmp_path, controller.health, clock=lambda: MOMENT,
        disk_usage=lambda _: SimpleNamespace(free=0),
    )
    assert evaluator.evaluate(_monitoring("live"))["creators"][0]["admission"][
        "reason"
    ] == "low_free_space"
    try:
        started = controller.start(
            "https://www.tiktok.com/@manual/live", str(tmp_path / "manual.mp4")
        )
        assert started["state"] == "resolving"
    finally:
        controller.shutdown()
