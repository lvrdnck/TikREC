"""Service/controller startup availability and durable transitions, all offline."""

import json
from io import BytesIO, StringIO
from threading import Event
from unittest.mock import patch

import pytest

from tests.test_reconciliation import (PAGE, SIGNED, keep_finalizer, no_call,
                                      reconciler, saved_session)
from tests.test_service import request
from tikrec.capture import CaptureResult
from tikrec.cli import main
from tikrec.job_state import JobStateStore
from tikrec.recording import RecordingBusy, RecordingController
from tikrec.service import RecordingHTTPServer
from tikrec.tiktok import LiveResolution, TikTokResolutionTransientError


def joined(controller):
    if controller._worker:
        controller._worker.join(2)
        assert not controller._worker.is_alive()


def test_empty_store_keeps_v04_idle_behavior(tmp_path):
    controller = RecordingController(store=JobStateStore(tmp_path / "job.json"))
    assert controller.status() == {"state": "idle", "active": False}
    assert controller.health()["available"]
    controller.shutdown()


def test_completed_job_does_not_recover_or_relaunch(tmp_path):
    store, job, _ = saved_session(tmp_path, state="completed", ended_at=1100,
                                  stop_requested=True, finalization_completed=True)
    controller = RecordingController(store=store, reconciler=reconciler(store, resolver=no_call))
    assert controller._worker is None and controller.health()["available"]
    assert controller.status()["session_id"] == job.session_id
    assert not controller.status()["resumed"]
    controller.shutdown()


def test_health_and_conflict_while_resolution_is_pending(tmp_path):
    store, job, _ = saved_session(tmp_path)
    entered, release = Event(), Event()
    def resolve(page):
        entered.set()
        assert release.wait(2)
        raise TikTokResolutionTransientError("DNS " + SIGNED)
    # Explicit single-attempt mode keeps the original deferred-result contract covered.
    controller = RecordingController(store=store, reconciler=reconciler(store, resolver=resolve), retry_policy=None)
    before = store.path.read_bytes()
    try:
        assert entered.wait(2)
        assert controller.status()["state"] == "reconciling"
        code, health = request(controller, "GET", "/health")
        assert code == 200 and health["active"] and not health["available"]
        assert request(controller, "POST", "/recording/start",
                       {"url": PAGE, "output": str(tmp_path / "new.mp4")})[0] == 409
        release.set()
        joined(controller)
        code, status = request(controller, "GET", "/recording")
        assert code == 200 and status["state"] == "recovering"
        assert status["recovery_state"] == "deferred" and not status["active"]
        assert status["session_id"] == job.session_id
        assert not controller.health()["available"]
        assert "secret" not in json.dumps(status)
        with pytest.raises(RecordingBusy):
            controller.start(PAGE, str(tmp_path / "new.mp4"))
    finally:
        release.set()
        controller.shutdown()
    assert store.path.read_bytes() == before


def test_stop_during_resolution_outranks_resume_and_is_durable(tmp_path):
    store, _, _ = saved_session(tmp_path)
    entered, release = Event(), Event()
    def resolve(page):
        entered.set()
        assert release.wait(2)
        return LiveResolution("123", SIGNED)
    controller = RecordingController(store=store, reconciler=reconciler(
        store, resolver=resolve, finalizer=keep_finalizer, resume_capture=no_call))
    try:
        assert entered.wait(2)
        controller.stop()
        assert store.load().stop_requested
        release.set()
        joined(controller)
        assert controller.status()["state"] == "completed"
        assert controller.status()["stop_requested"]
        assert store.load().stop_requested and store.load().resume_count == 0
    finally:
        release.set()
        controller.shutdown()


def test_resumed_worker_reuses_job_and_handles_normal_remote_stop(tmp_path):
    store, job, _ = saved_session(tmp_path, raw_copy_enabled=True)
    entered = Event()
    def resume(page, **options):
        assert store.load().resume_count == 1 and store.load().state == "resuming"
        assert options["session_id"] == job.session_id
        assert options["raw_copy_dir"] == tmp_path / "out.parts"
        options["state"]("recording")
        entered.set()
        assert options["stop_event"].wait(2)
        options["state"]("finalizing")
        keep_finalizer(tuple((tmp_path / "out.parts").glob("*.flv")), options["output_path"])
        return CaptureResult((), options["output_path"], True, resumed=True)
    controller = RecordingController(store=store, reconciler=reconciler(
        store, resolver=lambda _: LiveResolution("123", SIGNED), resume_capture=resume))
    try:
        assert entered.wait(2)
        status = controller.status()
        assert status["resumed"] and status["resume_count"] == 1
        assert status["session_id"] == job.session_id and status["state"] == "recording"
        assert request(controller, "POST", "/recording/stop", {})[1]["stop_requested"]
        joined(controller)
        assert controller.status()["state"] == "completed"
        assert store.load().finalization_completed and store.load().stop_requested
    finally:
        controller.shutdown()


@pytest.mark.parametrize("document", ["{", "{}"])
def test_invalid_saved_state_blocks_start_and_preserves_file(tmp_path, document):
    store = JobStateStore(tmp_path / "job.json")
    store.path.write_text(document)
    controller = RecordingController(store=store)
    assert controller.status()["recovery_state"] == "failed"
    assert not controller.health()["available"]
    assert request(controller, "POST", "/recording/start",
                   {"url": PAGE, "output": str(tmp_path / "new.mp4")})[0] == 409
    controller.shutdown()
    assert store.path.read_text() == document


def test_normal_start_identity_stop_and_completion_are_persisted(tmp_path):
    store = JobStateStore(tmp_path / "job.json")
    entered = Event()
    def capture(page, **options):
        assert store.load().state == "resolving" and store.load().room_id is None
        options["room_identity"]("123")
        assert store.load().room_id == "123"
        options["state"]("recording")
        entered.set()
        assert options["stop_event"].wait(2)
        assert store.load().stop_requested
        options["state"]("finalizing")
        assert store.load().state == "finalizing"
        return CaptureResult((), None, True)
    controller = RecordingController(capture=capture, store=store)
    controller.start(PAGE, str(tmp_path / "out.mp4"))
    try:
        assert entered.wait(2)
        controller.stop()
        joined(controller)
        assert store.load().state == "completed" and not store.load().finalization_completed
    finally:
        controller.shutdown()


@pytest.mark.parametrize("recovery", ["reconciling", "resuming", "deferred", "failed"])
def test_remote_cli_renders_recovery_json_without_traceback(monkeypatch, recovery):
    monkeypatch.delenv("TIKREC_TOKEN", raising=False)
    output, errors = StringIO(), StringIO()
    result = {"state": "recovering", "recovery_state": recovery,
              "recovery_reason": "identity_unavailable"}
    exit_code = main(["remote", "status", "--server", "http://main-pc"], stdout=output,
                     stderr=errors, remote_opener=lambda *a, **k: BytesIO(json.dumps(result).encode()))
    assert exit_code == (1 if recovery in {"deferred", "failed"} else 0)
    assert json.loads(output.getvalue()) == result and errors.getvalue() == ""


def test_failed_socket_bind_cannot_launch_startup_recovery():
    with patch("tikrec.service.ThreadingHTTPServer.__init__", side_effect=OSError("busy")):
        with patch("tikrec.service.RecordingController") as controller:
            with pytest.raises(OSError):
                RecordingHTTPServer()
            controller.assert_not_called()


def test_recovery_thread_start_failure_keeps_previous_intent(tmp_path):
    store, job, _ = saved_session(tmp_path)
    with patch("tikrec.recording.Thread.start", side_effect=RuntimeError("failed")):
        controller = RecordingController(store=store)
    assert controller.status()["recovery_state"] == "failed"
    assert not controller.health()["available"] and store.load() == job
    controller.shutdown()


def test_resumed_worker_failure_remains_nonterminal_and_blocks_new_start(tmp_path):
    store, _, _ = saved_session(tmp_path)
    def resume(page, **options):
        raise ValueError("storage changed " + SIGNED)
    controller = RecordingController(store=store, reconciler=reconciler(
        store, resolver=lambda _: LiveResolution("123", SIGNED), resume_capture=resume))
    joined(controller)
    assert controller.status()["recovery_state"] == "failed"
    assert store.load().needs_reconciliation and store.load().resume_count == 1
    assert not controller.health()["available"]
    with pytest.raises(RecordingBusy):
        controller.start(PAGE, str(tmp_path / "new.mp4"))
    assert "secret" not in json.dumps(controller.status())
    controller.shutdown()
