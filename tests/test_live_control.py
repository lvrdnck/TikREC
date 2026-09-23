"""Exercise the real writer/manifest path with fake offline media sources."""

import json
from threading import Event

import pytest

from tikrec.capture import CaptureError
from tikrec.live import capture_live
from tikrec.tiktok import TikTokOfflineError
from tests.test_live import stream


PAGE = "https://www.tiktok.com/@Alpha/live"


def test_stop_closes_part_finalizes_and_updates_manifest(tmp_path):
    event = Event()
    states = []
    closed = []
    retained_bytes = []
    output = tmp_path / "out.mp4"

    def source(_):
        try:
            yield from stream()
            event.set()
            yield stream()[-1]
        finally:
            closed.append(True)

    def finalizer(parts, path):
        assert event.is_set()
        retained_bytes.extend(p.read_bytes() for p in parts)
        path.write_bytes(b"output")
        return path

    result = capture_live(
        PAGE, parts_directory=tmp_path / "parts", output_path=output,
        resolver=lambda _: "https://cdn.test/a.flv?secret=signed",
        tag_source=source, finalizer=finalizer, stop_event=event,
        state=states.append, session_id="job-id", media_inspector=lambda _: None,
    )
    assert result.interrupted
    assert result.output_path == output
    assert len(result.parts) == 1
    assert result.parts[0].read_bytes() == retained_bytes[0]
    assert closed == [True]
    assert states == ["resolving", "recording", "finalizing"]
    manifest = json.loads((tmp_path / "parts/session.json").read_text())
    assert manifest["session_id"] == "job-id"
    assert manifest["creator"] == "alpha"
    assert manifest["status"] == "interrupted"
    assert manifest["finalization"]["status"] == "completed"
    assert "signed" not in json.dumps(manifest)


def test_finalization_failure_preserves_part_and_reports_failed_manifest(tmp_path):
    event = Event()

    def source(_):
        yield from stream()
        event.set()

    def finalizer(parts, output):
        raise OSError("disk full")

    with pytest.raises(CaptureError, match="finalization failed") as failure:
        capture_live(
            PAGE, parts_directory=tmp_path / "parts",
            output_path=tmp_path / "out.mp4", resolver=lambda _: "flv",
            tag_source=source, finalizer=finalizer, stop_event=event,
        )
    assert failure.value.parts[0].is_file()
    manifest = json.loads((tmp_path / "parts/session.json").read_text())
    assert manifest["status"] == "failed"
    assert manifest["finalization"]["status"] == "failed"


def test_stop_before_resolution_creates_no_empty_session(tmp_path):
    event = Event()
    event.set()
    result = capture_live(PAGE, parts_directory=tmp_path / "parts", stop_event=event)
    assert result.interrupted and not result.parts
    assert not (tmp_path / "parts").exists()


def test_ctrl_c_during_retry_finalizes_retained_parts(tmp_path):
    def sleeper(_):
        raise KeyboardInterrupt()

    calls = []

    def finalizer(parts, output):
        calls.append(tuple(parts))
        output.write_bytes(b"ok")
        return output

    result = capture_live(
        PAGE, parts_directory=tmp_path / "parts", output_path=tmp_path / "out.mp4",
        resolver=lambda _: "flv", tag_source=lambda _: iter(stream()),
        sleeper=sleeper, finalizer=finalizer, media_inspector=lambda _: None,
    )
    assert result.interrupted and calls == [result.parts]


def test_stop_during_offline_confirmation_finalizes(tmp_path):
    class StopOnConfirmation(Event):
        def wait(self, timeout=None):
            if timeout == 5:
                self.set()
            return super().wait(timeout)

    event = StopOnConfirmation()
    attempts = []

    def resolver(_):
        attempts.append(True)
        if len(attempts) > 1:
            raise TikTokOfflineError("offline")
        return "flv"

    result = capture_live(
        PAGE, parts_directory=tmp_path / "parts", resolver=resolver,
        tag_source=lambda _: iter(stream()), stop_event=event,
        backoff_seconds=0,
    )
    assert result.interrupted and len(result.parts) == 1
    assert len(attempts) == 2


def test_healthy_reconnect_gap_omits_configured_failure_backoff(tmp_path):
    now = [100.0]
    attempts = []

    def resolver(_):
        attempts.append(True)
        if len(attempts) == 3:
            raise TikTokOfflineError("offline")
        return "flv"

    def sleeper(delay):
        now[0] += delay

    result = capture_live(
        PAGE, parts_directory=tmp_path / "parts", resolver=resolver,
        tag_source=lambda _: iter(stream()), clock=lambda: now[0],
        sleeper=sleeper, backoff_seconds=2, offline_confirmation_checks=1,
    )
    assert result.connections[1].gap_before == 0
    assert result.connections[1].started_at == 100
