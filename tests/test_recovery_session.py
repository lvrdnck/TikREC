"""Conservative output inspection and retry-safe finalization recovery."""

import json

import pytest

from tests.test_reconciliation import keep_finalizer, no_call, reconciler, saved_session
from tests.test_session_resume import update
from tikrec.media import MediaInfo
from tikrec.recovery_session import completed_output_is_proven, inspect_recovery_session


@pytest.mark.parametrize("info", [
    None, MediaInfo(), MediaInfo(video_codec="h264", format_name="mp4", duration_seconds=0),
    MediaInfo(video_codec="h264", format_name="mp4", duration_seconds=float("inf")),
    MediaInfo(video_codec="h264", format_name="mp4", duration_seconds=True),
    MediaInfo(video_codec="hevc", format_name="mp4", duration_seconds=1),
])
def test_incomplete_or_mismatched_output_proof_is_rejected(tmp_path, info):
    _, job, manifest = saved_session(tmp_path, state="finalizing")
    output = tmp_path / "out.mp4"
    output.write_bytes(b"keep")
    manifest.complete(tuple((tmp_path / "out.parts").glob("*.flv")), output_path=output,
                      finalization_status="completed")
    update(tmp_path / "out.parts", media={"video_codec": "h264", "audio_codec": None,
                                        "width": None, "height": None})
    session = inspect_recovery_session(job, clock=lambda: 2000, media_inspector=lambda _: None)
    assert not completed_output_is_proven(session, output, lambda _: info)
    assert output.read_bytes() == b"keep"


def test_failed_recovery_finalization_can_retry_safely_when_output_absent(tmp_path):
    store, _, _ = saved_session(tmp_path, stop_requested=True)
    def failure(parts, output):
        raise OSError("encoder failed")
    first = reconciler(store, resolver=no_call, finalizer=failure).reconcile()
    assert first.outcome == "failed" and store.load().state == "finalizing"
    facts = json.loads((tmp_path / "out.parts/session.json").read_text())
    assert facts["ended_at"] == 2000 and facts["finalization"]["status"] == "failed"
    second = reconciler(store, resolver=no_call, finalizer=keep_finalizer).reconcile()
    assert second.outcome == "settled" and store.load().finalization_completed


def test_running_finalization_with_absent_output_and_no_partial_can_retry(tmp_path):
    store, _, manifest = saved_session(tmp_path, state="finalizing")
    manifest.mark_finalizing(tuple((tmp_path / "out.parts").glob("*.flv")))
    result = reconciler(store, resolver=no_call, finalizer=keep_finalizer).reconcile()
    assert result.outcome == "settled"


def test_missing_session_storage_blocks_recovery_without_creating_it(tmp_path):
    store, job, _ = saved_session(tmp_path)
    (tmp_path / "out.parts/session.json").unlink()
    assert reconciler(store, resolver=no_call).reconcile().blocked
    assert not (tmp_path / "out.parts/session.json").exists()
