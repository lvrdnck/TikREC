"""Patient startup decisions preserve original intent and never require network/FFmpeg."""

import json
import socket
from urllib.error import HTTPError, URLError

import pytest

from tests.test_live_recovery import FakeClock
from tests.test_reconciliation import SIGNED, keep_finalizer, no_call, saved_session
from tikrec.capture_control import CaptureControl
from tikrec.reconciliation import StartupReconciler
from tikrec.retry_policy import RetryPolicy
from tikrec.tiktok import LiveResolution, TikTokOfflineError, TikTokResolutionError


def run_reconciliation(store, resolve, *, clock, **options):
    recovery = StartupReconciler(store, resolver=resolve, finalizer=keep_finalizer,
                                clock=clock, media_inspector=lambda _: None)
    return recovery.reconcile(retry_policy=RetryPolicy(window_seconds=20), recovery_clock=clock,
                              control=CaptureControl(None, clock.sleep), **options)


@pytest.mark.parametrize("result_kind", ["same", "offline", "different"])
def test_startup_patient_dns_recovers_and_settles_proven_identity(tmp_path, result_kind):
    store, job, _ = saved_session(tmp_path)
    clock, calls, status = FakeClock(), [], []
    def resolve(page):
        calls.append(page)
        if len(calls) <= 3:
            raise URLError(socket.gaierror(socket.EAI_AGAIN, "DNS " + SIGNED))
        if result_kind == "offline":
            raise TikTokOfflineError("offline", status=4)
        return LiveResolution("123" if result_kind == "same" else "456", SIGNED)
    result = run_reconciliation(store, resolve, clock=clock, recovery_observer=status.append)
    assert clock.delays == [1, 2, 5] and len(calls) == 4
    assert result.outcome == ("resume" if result_kind == "same" else "settled")
    assert result.job.session_id == job.session_id and result.job.room_id == "123"
    assert result.job.resume_count == (1 if result_kind == "same" else 0)
    assert "secret" not in store.path.read_text()
    evidence = (tmp_path / "out.parts/connections.jsonl").read_text()
    assert "secret" not in evidence
    assert [s["retry_attempt"] for s in status if s["phase"] == "wait"] == [1, 2, 3]


def test_startup_exhaustion_is_terminal_without_output_or_offline_claim(tmp_path):
    store, job, _ = saved_session(tmp_path)
    clock, calls = FakeClock(), []
    def resolve(page):
        calls.append(page)
        raise socket.gaierror("DNS")
    recovery = StartupReconciler(store, resolver=resolve, finalizer=no_call, clock=clock,
                                media_inspector=lambda _: None)
    result = recovery.reconcile(retry_policy=RetryPolicy(window_seconds=4), recovery_clock=clock,
                                control=CaptureControl(None, clock.sleep))
    assert result.outcome == "exhausted" and not result.blocked
    assert result.reason == "outage_timeout" and store.load().state == "failed"
    assert store.load().session_id == job.session_id and not store.load().finalization_completed
    assert clock.delays == [1, 2, 1] and len(calls) == 3
    assert not (tmp_path / "out.mp4").exists()
    facts = json.loads((tmp_path / "out.parts/session.json").read_text())
    assert facts["finalization"]["status"] == "not_started" and facts["status"] == "failed"


@pytest.mark.parametrize("error", [
    TikTokResolutionError("malformed payload"), PermissionError("local permission"),
    RuntimeError("programming"), HTTPError(SIGNED, 404, "missing", {}, None),
])
def test_startup_nonretryable_failure_is_not_polled(tmp_path, error):
    store, _, _ = saved_session(tmp_path)
    clock, calls = FakeClock(), []
    def resolve(page):
        calls.append(page)
        raise error
    result = run_reconciliation(store, resolve, clock=clock)
    assert result.outcome == "failed" and len(calls) == 1 and clock.delays == []
    assert store.load().needs_reconciliation


def test_process_death_during_wait_leaves_nonterminal_resumable_job(tmp_path):
    store, job, manifest = saved_session(tmp_path)
    original_manifest = manifest.path.read_bytes()
    clock = FakeClock()
    class SimulatedCrash(BaseException):
        pass
    def wait(seconds):
        durable = store.load()
        assert durable.state == "recovering_network" and durable.recovery_reason == "network_outage"
        raise SimulatedCrash()
    def resolve(page):
        raise socket.gaierror("DNS")
    recovery = StartupReconciler(store, resolver=resolve, clock=clock, media_inspector=lambda _: None)
    with pytest.raises(SimulatedCrash):
        recovery.reconcile(retry_policy=RetryPolicy(), recovery_clock=clock,
                            control=CaptureControl(None, wait))
    assert store.load().may_resume and manifest.path.read_bytes() == original_manifest
    restarted = StartupReconciler(store, resolver=lambda _: LiveResolution("123", SIGNED), clock=clock,
                                  media_inspector=lambda _: None).reconcile()
    assert restarted.outcome == "resume" and restarted.job.session_id == job.session_id
    assert restarted.job.resume_count == 1


def test_startup_retry_after_is_capped_and_clock_driven(tmp_path):
    store, _, _ = saved_session(tmp_path)
    clock, calls = FakeClock(), []
    def resolve(page):
        calls.append(page)
        if len(calls) == 1:
            raise HTTPError(SIGNED, 503, "busy", {"Retry-After": "9999"}, None)
        return LiveResolution("123", SIGNED)
    recovery = StartupReconciler(store, resolver=resolve, clock=clock, media_inspector=lambda _: None)
    result = recovery.reconcile(retry_policy=RetryPolicy(), recovery_clock=clock,
                                control=CaptureControl(None, clock.sleep))
    assert result.outcome == "resume" and clock.delays == [30]


def test_malformed_result_after_dns_is_failure_without_false_recovered_event(tmp_path):
    store, _, _ = saved_session(tmp_path)
    clock, calls = FakeClock(), []
    def resolve(page):
        calls.append(page)
        if len(calls) == 1:
            raise socket.gaierror("DNS")
        return {"room_id": "123", "flv_url": SIGNED}
    result = run_reconciliation(store, resolve, clock=clock)
    assert result.outcome == "failed" and len(calls) == 2
    records = [json.loads(line) for line in (tmp_path / "out.parts/connections.jsonl").read_text().splitlines()]
    assert not any(e.get("phase") == "recovered" for e in records)
