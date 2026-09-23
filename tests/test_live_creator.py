"""Manual and automatic controller sessions retain page-derived creator metadata."""

import json
from pathlib import Path

import pytest

from tests.test_live import _finalizer, stream
from tikrec.live import capture_live
from tikrec.recording import RecordingController
from tikrec.tiktok import TikTokOfflineError
from tikrec.tiktok_identity import LiveResolution


@pytest.mark.parametrize("automatic", [False, True])
def test_controller_live_manifest_creator_is_canonical(tmp_path: Path, automatic: bool) -> None:
    actions = iter((LiveResolution("123", "https://cdn.test/live.flv?token=private"),
                    TikTokOfflineError("offline")))
    def resolver(_):
        item = next(actions)
        if isinstance(item, Exception):
            raise item
        return item
    def capture(page, **options):
        chosen = options.pop("resolver", resolver)
        options.pop("bound_resolver", None)
        return capture_live(page, resolver=chosen, tag_source=lambda _: iter(stream()),
                            finalizer=_finalizer, sleeper=lambda _: None,
                            offline_confirmation_checks=1, **options)
    controller = RecordingController(capture=capture,
                                     automatic_resolvers=lambda _: {"resolver": resolver})
    output = tmp_path / "alpha.mp4"
    try:
        options = {"expected_room_id": "123"} if automatic else {}
        controller.start("https://www.tiktok.com/@Alpha/live", str(output), **options)
        controller._worker.join(3)
        assert not controller._worker.is_alive()
        assert controller.status()["state"] == "completed"
        document = json.loads((tmp_path / "alpha.parts/session.json").read_text())
        assert document["creator"] == "alpha" and document["room_id"] == "123"
        assert "private" not in str(document)
    finally:
        controller.shutdown()
