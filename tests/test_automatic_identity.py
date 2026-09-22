"""Offline room-binding tests for unattended capture starts."""

from pathlib import Path

import pytest

from tikrec.automatic_identity import expected_room_resolvers
from tikrec.capture import CaptureError, CaptureResult
from tikrec.live import capture_live
from tikrec.recording import RecordingController
from tikrec.tiktok import TikTokResolutionError
from tikrec.tiktok_identity import LiveResolution


PAGE = "https://www.tiktok.com/@creator/live"
SIGNED = "https://cdn.test/live.flv?secret=discard"


def test_expected_room_guard_accepts_only_matching_canonical_identity():
    calls = []
    options = expected_room_resolvers(
        "123",
        resolver=lambda page: calls.append(("initial", page)) or LiveResolution("00123", SIGNED),
        bound_resolver=lambda page, room: (
            calls.append(("bound", page, room)) or LiveResolution("123", SIGNED)
        ),
    )
    assert options["resolver"](PAGE).room_id == "123"
    assert options["bound_resolver"](PAGE, "123").room_id == "123"
    assert calls == [("initial", PAGE), ("bound", PAGE, "123")]


@pytest.mark.parametrize("resolution", [
    "https://cdn.test/live.flv?secret=hidden",
    LiveResolution("456", SIGNED),
])
def test_expected_room_guard_rejects_missing_or_changed_identity(resolution):
    guard = expected_room_resolvers("123", resolver=lambda _: resolution)["resolver"]
    with pytest.raises(TikTokResolutionError) as failure:
        guard(PAGE)
    assert "secret" not in str(failure.value)


@pytest.mark.parametrize("resolution", [
    "https://cdn.test/live.flv?secret=hidden",
    LiveResolution("456", SIGNED),
])
def test_identity_failure_precedes_session_or_media_creation(
    tmp_path: Path, resolution
):
    media_calls = []
    options = expected_room_resolvers("123", resolver=lambda _: resolution)
    with pytest.raises(CaptureError, match="resolution failed"):
        capture_live(
            PAGE,
            parts_directory=tmp_path / "out.parts",
            output_path=tmp_path / "out.mp4",
            tag_source=lambda _: media_calls.append(True) or iter(()),
            **options,
        )
    assert media_calls == []
    assert not (tmp_path / "out.parts").exists()
    assert not (tmp_path / "out.mp4").exists()


def test_controller_passes_room_guard_only_for_internal_automatic_start(tmp_path: Path):
    calls = []

    def guards(room_id):
        calls.append(("guard", room_id))
        return {"resolver": lambda _: None, "bound_resolver": lambda *_: None}

    def capture(url, **kwargs):
        calls.append((url, kwargs))
        return CaptureResult((), None)

    controller = RecordingController(capture=capture, automatic_resolvers=guards)
    controller.start(PAGE, str(tmp_path / "auto.mp4"), expected_room_id="00123")
    controller._worker.join(2)
    controller.start(PAGE, str(tmp_path / "manual.mp4"))
    controller.shutdown()
    assert calls[0] == ("guard", "123")
    assert "resolver" in calls[1][1] and "bound_resolver" in calls[1][1]
    assert "raw_copy_dir" not in calls[1][1]
    assert "resolver" not in calls[2][1] and "bound_resolver" not in calls[2][1]


def test_controller_rejects_invalid_internal_expected_room_before_reserving_slot(
    tmp_path: Path,
):
    controller = RecordingController()
    with pytest.raises(ValueError, match="invalid public room"):
        controller.start(PAGE, str(tmp_path / "out.mp4"), expected_room_id="00123bad")
    assert controller.health()["available"]
