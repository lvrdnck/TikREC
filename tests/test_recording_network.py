"""HTTP availability, durable recovery transitions and cancellation with injected waits."""

import json
import socket
from functools import partial
from threading import Event, Thread

from tests.test_capture_resume import stream
from tests.test_live_recovery import FakeClock
from tests.test_reconciliation import PAGE, SIGNED, keep_finalizer, saved_session
from tests.test_recording_startup import joined
from tests.test_service import request
from tikrec.job_state import JobStateStore
from tikrec.capture import CaptureResult
from tikrec.live import capture_live
from tikrec.live_resume import capture_live_resume
from tikrec.recording import RecordingController
from tikrec.reconciliation import StartupReconciler
from tikrec.retry_policy import RetryPolicy
from tikrec.tiktok import LiveResolution, TikTokOfflineError, TikTokResolutionError


def test_startup_network_wait_keeps_health_status_and_stop_responsive(tmp_path):
    store, job, _ = saved_session(tmp_path)
    clock, waiting = FakeClock(), Event()
    def resolve(page):
        raise socket.gaierror("DNS " + SIGNED)
    def waiter(event, seconds):
        waiting.set()
        assert event.wait(2)  # Synchronize with remote stop; no backoff sleeping.
    recovery = StartupReconciler(store, resolver=resolve, finalizer=keep_finalizer,
                                clock=clock, media_inspector=lambda _: None)
    controller = RecordingController(store=store, reconciler=recovery, clock=clock,
                                      recovery_clock=clock, recovery_waiter=waiter)
    try:
        assert waiting.wait(2)
        durable = store.load()
        assert durable.state == "recovering_network" and durable.recovery_reason == "network_outage"
        health = request(controller, "GET", "/health")[1]
        assert health["active"] and not health["available"]
        status = request(controller, "GET", "/recording")[1]
        assert status["retry_attempt"] == 1 and status["next_retry_in_seconds"] == 1
        assert status["network_failure_kind"] == "dns"
        clock.now += 0.5
        assert controller.status()["next_retry_in_seconds"] == 0.5
        assert controller.status()["outage_elapsed_seconds"] == 0.5
        assert request(controller, "POST", "/recording/start",
                       {"url": PAGE, "output": str(tmp_path / "new.mp4")})[0] == 409
        request(controller, "POST", "/recording/stop", {})
        joined(controller)
        assert store.load().stop_requested and store.load().finalization_completed
        assert controller.status()["state"] == "completed" and controller.status()["resume_count"] == 0
        assert "secret" not in json.dumps(controller.status())
        assert store.load().session_id == job.session_id
    finally:
        controller.shutdown()


def test_nonretryable_resolver_failure_closes_active_retry_countdown(tmp_path):
    clock, calls = FakeClock(), []
    def resolve(page):
        calls.append(page)
        if len(calls) == 1:
            return LiveResolution("123", SIGNED)
        if len(calls) == 2:
            raise socket.gaierror("DNS")
        raise TikTokResolutionError("malformed room data")
    capture = partial(capture_live, resolver=resolve, tag_source=lambda _: iter(stream()),
                      clock=clock, manifest_clock=clock, media_inspector=lambda _: None)
    controller = RecordingController(capture=capture, clock=clock,
        recovery_clock=clock, recovery_waiter=lambda event, seconds: clock.sleep(seconds))
    controller.start(PAGE, str(tmp_path / "out.mp4"))
    joined(controller)
    status = controller.status()
    assert status["state"] == status["recovery_state"] == "failed"
    assert status["next_retry_in_seconds"] == 0 and status["recovery_reason"] is None
    assert len(calls) == 3 and not (tmp_path / "out.mp4").exists()
    controller.shutdown()


def test_shutdown_wakes_startup_patient_wait_and_finalizes(tmp_path):
    store, _, _ = saved_session(tmp_path)
    clock, waiting = FakeClock(), Event()
    def resolve(page):
        raise socket.gaierror("DNS")
    def waiter(event, seconds):
        waiting.set()
        assert event.wait(2)
    recovery = StartupReconciler(store, resolver=resolve, finalizer=keep_finalizer,
                                clock=clock, media_inspector=lambda _: None)
    controller = RecordingController(store=store, reconciler=recovery, clock=clock,
                                      recovery_clock=clock, recovery_waiter=waiter)
    assert waiting.wait(2)
    shutdown = Thread(target=controller.shutdown)
    shutdown.start()
    shutdown.join(2)
    assert not shutdown.is_alive() and store.load().stop_requested
    assert store.load().finalization_completed


def test_active_outage_exhaustion_releases_service_and_survives_restart(tmp_path):
    store = JobStateStore(tmp_path / "job.json")
    clock, calls, transitions = FakeClock(), [], []
    save = store.save
    def record_save(job):
        transitions.append((job.state, job.recovery_reason))
        save(job)
    store.save = record_save
    def resolve(page):
        calls.append(page)
        if len(calls) == 1:
            return LiveResolution("123", SIGNED)
        raise socket.gaierror("DNS " + SIGNED)
    def waiter(event, seconds):
        clock.sleep(seconds)
    capture = partial(capture_live, resolver=resolve, tag_source=lambda _: iter(stream()),
                      clock=clock, manifest_clock=clock, media_inspector=lambda _: None)
    controller = RecordingController(capture=capture, store=store, clock=clock,
        retry_policy=RetryPolicy(window_seconds=4), recovery_clock=clock, recovery_waiter=waiter)
    controller.start(PAGE, str(tmp_path / "out.mp4"))
    joined(controller)
    status = controller.status()
    assert status["state"] == "failed" and status["recovery_reason"] == "outage_timeout"
    assert status["recovery_state"] == "exhausted" and controller.health()["available"]
    assert ("recovering_network", "network_outage") in transitions
    assert transitions[-1] == ("failed", "outage_timeout")
    assert len(transitions) < len(calls) + 6
    assert not (tmp_path / "out.mp4").exists() and status["part_count"] == 1
    assert "secret" not in store.path.read_text() and "secret" not in json.dumps(status)
    controller.shutdown()
    restarted = RecordingController(store=store)
    assert restarted._worker is None and restarted.health()["available"]
    assert restarted.status()["session_id"] == status["session_id"]
    restarted.shutdown()


def test_active_remote_stop_during_dns_wait_finalizes_retained_media(tmp_path):
    store = JobStateStore(tmp_path / "job.json")
    clock, calls, waiting = FakeClock(), [], Event()
    def resolve(page):
        calls.append(page)
        if len(calls) == 1:
            return LiveResolution("123", SIGNED)
        raise socket.gaierror("DNS")
    def finalizer(parts, output):
        assert len(parts) == 1 and store.load().stop_requested
        output.write_bytes(b"final")
        return output
    def waiter(event, seconds):
        if store.load().recovery_reason == "network_outage":
            waiting.set()
            assert event.wait(2)
        else:
            clock.sleep(seconds)
    capture = partial(capture_live, resolver=resolve, tag_source=lambda _: iter(stream()),
                      finalizer=finalizer, clock=clock, manifest_clock=clock, media_inspector=lambda _: None)
    controller = RecordingController(capture=capture, store=store, clock=clock,
                                      recovery_clock=clock, recovery_waiter=waiter)
    controller.start(PAGE, str(tmp_path / "out.mp4"))
    try:
        assert waiting.wait(2)
        assert controller.status()["network_failure_kind"] == "dns"
        request(controller, "POST", "/recording/stop", {})
        joined(controller)
        assert controller.status()["interrupted"] and controller.status()["state"] == "completed"
        assert store.load().stop_requested and store.load().finalization_completed
        assert len(calls) == 2
    finally:
        controller.shutdown()


def test_startup_exhaustion_releases_slot_for_new_explicit_job(tmp_path):
    store, old_job, _ = saved_session(tmp_path)
    clock = FakeClock()
    def resolve(page):
        raise socket.gaierror("DNS")
    recovery = StartupReconciler(store, resolver=resolve, clock=clock, media_inspector=lambda _: None)
    controller = RecordingController(store=store, reconciler=recovery, clock=clock,
        capture=lambda *a, **k: CaptureResult((), None),
        retry_policy=RetryPolicy(window_seconds=4), recovery_clock=clock,
        recovery_waiter=lambda event, seconds: clock.sleep(seconds))
    joined(controller)
    assert controller.health()["available"] and controller.status()["recovery_state"] == "exhausted"
    assert controller.status()["recovery_reason"] == "outage_timeout"
    accepted = controller.start(PAGE, str(tmp_path / "new.mp4"))
    joined(controller)
    assert accepted["session_id"] != old_job.session_id
    assert len(list((tmp_path / "out.parts").glob("*.flv"))) == 2
    controller.shutdown()


def test_startup_network_recovers_then_runs_real_explicit_resume_offline(tmp_path):
    store, job, _ = saved_session(tmp_path)
    clock, calls, transitions = FakeClock(), [], []
    save = store.save
    def record_save(updated):
        transitions.append((updated.state, updated.recovery_reason))
        save(updated)
    store.save = record_save
    def resolve(page):
        calls.append(page)
        if len(calls) <= 2:
            raise socket.gaierror("DNS")
        if len(calls) == 3:
            return LiveResolution("123", SIGNED)
        raise TikTokOfflineError("offline", status=4)
    def finalizer(parts, output):
        assert len(parts) == 3
        output.write_bytes(b"final")
        return output
    resume = partial(capture_live_resume, tag_source=lambda _: iter(stream()), clock=clock,
                     observation_clock=clock, offline_confirmation_checks=1)
    recovery = StartupReconciler(store, resolver=resolve, resume_capture=resume, finalizer=finalizer,
                                clock=clock, media_inspector=lambda _: None)
    controller = RecordingController(store=store, reconciler=recovery, clock=clock, recovery_clock=clock,
                                      recovery_waiter=lambda event, seconds: clock.sleep(seconds))
    joined(controller)
    assert controller.status()["state"] == "completed" and controller.status()["resume_count"] == 1
    assert store.load().session_id == job.session_id and store.load().finalization_completed
    assert ("recovering_network", "network_outage") in transitions
    assert ("reconciling", "network_recovered") in transitions
    assert ("resuming", "process_restart") in transitions
    assert (tmp_path / "out.parts/part-0003.flv").exists()
    controller.shutdown()
