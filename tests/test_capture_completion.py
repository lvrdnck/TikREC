"""Source closure is separate from completed MP4 assembly."""

import json

from tests.test_live import stream
from tikrec.live import capture_live
from tikrec.tiktok import TikTokOfflineError, _ResolvedLiveUrl


def test_internal_completion_retains_requested_output_without_starting_finalizer(tmp_path):
    actions = iter((_ResolvedLiveUrl("https://fixture.invalid/flv", 2, room_id="123"),
                    TikTokOfflineError("offline")))

    def resolve(_):
        value = next(actions)
        if isinstance(value, Exception):
            raise value
        return value

    def forbidden(*_args, **_kwargs):
        raise AssertionError("internal capture must not assemble")

    output = tmp_path / "capture.mp4"
    result = capture_live("https://www.tiktok.com/@creator/live",
                          parts_directory=output.with_suffix(".parts"), output_path=output,
                          resolver=resolve, tag_source=lambda _: iter(stream()),
                          finalizer=forbidden, offline_confirmation_checks=1,
                          sleeper=lambda _: None, _capture_only=True)
    assert result.source_ended and result.requested_output == output
    assert result.finalization_pending and len(result.parts) == 1
    assert not output.exists()
    manifest = json.loads((output.with_suffix(".parts") / "session.json").read_text())
    assert manifest["output_path"] == str(output)
    assert manifest["finalization"]["status"] == "pending"
    assert manifest["ended_at"] is not None
