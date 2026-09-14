"""Offline checks for retained-session lifecycle helpers."""

from tikrec.live_session import fail_live, finish_live
from tikrec.manifest import SessionManifest


def test_empty_unstarted_session_finishes_without_storage(tmp_path):
    directory = tmp_path / "parts"
    manifest = SessionManifest(directory, None, "tiktok_live")
    result = finish_live([], None, manifest=manifest, records=[], finalizer=None,
                         state=None, progress=None)
    assert result.parts == () and not directory.exists()


def test_unstarted_failure_retains_reported_parts_without_storage(tmp_path):
    manifest = SessionManifest(tmp_path / "parts", None, "tiktok_live")
    part = tmp_path / "part.flv"
    failure = fail_live("failure", [part], manifest=manifest, output_path=None)
    assert failure.parts == (part,) and not manifest.path.exists()
