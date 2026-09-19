"""Real writer outage continuation with fake resolver/source/clock/finalizer."""

import errno
import json
import socket
from urllib.error import HTTPError, URLError

import pytest

from tests.test_capture_resume import stream
from tests.test_reconciliation import PAGE, SIGNED
from tests.test_writer import read_part
from tikrec.capture import CaptureError
from tikrec.live import capture_live
from tikrec.live_recovery import OutageCaptureError
from tikrec.retry_policy import RetryPolicy
from tikrec.tiktok import LiveResolution, TikTokOfflineError, TikTokResolutionError


class FakeClock:
    def __init__(self):
        self.now, self.delays = 1000.0, []
    def __call__(self):
        return self.now
    def sleep(self, delay):
        self.delays.append(delay)
        self.now += delay


def run_capture(tmp_path, resolver, source, *, clock=None, **options):
    clock = clock or FakeClock()
    def finalizer(parts, output):
        output.write_bytes(b"final")
        return output
    return capture_live(PAGE, parts_directory=tmp_path / "out.parts", output_path=tmp_path / "out.mp4",
        resolver=resolver, tag_source=source, finalizer=finalizer, clock=clock,
        manifest_clock=clock, observation_clock=clock, recovery_clock=clock,
        sleeper=clock.sleep, media_inspector=lambda _: None, offline_confirmation_checks=1, **options)


def events(tmp_path):
    return [json.loads(line) for line in (tmp_path / "out.parts/connections.jsonl").read_text().splitlines()]


@pytest.mark.parametrize("finish", ["same", "offline", "different"])
def test_dns_after_eof_survives_more_than_three_failures_and_proves_room_identity(tmp_path, finish):
    clock, calls, sources, status = FakeClock(), [], [], []
    def resolve(page):
        calls.append(page)
        if len(calls) == 1:
            return LiveResolution("123", SIGNED)
        if len(calls) <= 5:
            raise URLError(socket.gaierror(socket.EAI_AGAIN, "DNS " + SIGNED))
        if len(calls) == 6 and finish != "offline":
            return LiveResolution("123" if finish == "same" else "456", SIGNED + "2")
        raise TikTokOfflineError("offline", status=4, room_id="123")
    def source(url):
        sources.append(url)
        return iter(stream(90000 if len(sources) == 1 else 10))
    result = run_capture(tmp_path, resolve, source, clock=clock, recovery_observer=status.append)
    assert clock.delays[:5] == [0, 1, 2, 5, 10]
    assert sources == ([SIGNED, SIGNED + "2"] if finish == "same" else [SIGNED])
    assert len(result.parts) == (2 if finish == "same" else 1)
    assert read_part(result.parts[-1])[0].timestamp == 0
    assert status[0]["phase"] == "entered" and status[0]["network_failure_kind"] == "dns"
    assert max(s["retry_attempt"] for s in status) == 4
    phases = [e["phase"] for e in events(tmp_path) if e.get("event") == "network_recovery"]
    assert phases == ["entered", {"same": "recovered", "offline": "offline", "different": "live_changed"}[finish]]
    assert "secret" not in json.dumps(events(tmp_path))
    assert all(page == PAGE for page in calls)


def test_sustained_dns_exhausts_without_finalization_or_confirmed_offline(tmp_path):
    clock, calls = FakeClock(), []
    def resolve(page):
        calls.append(page)
        if len(calls) == 1:
            return LiveResolution("123", SIGNED)
        raise socket.gaierror(socket.EAI_AGAIN, "DNS " + SIGNED)
    with pytest.raises(OutageCaptureError) as failure:
        run_capture(tmp_path, resolve, lambda _: iter(stream()), clock=clock,
                    retry_policy=RetryPolicy(window_seconds=4))
    assert clock.delays == [0, 1, 2, 1] and len(calls) == 4
    assert len(failure.value.parts) == 1 and not (tmp_path / "out.mp4").exists()
    facts = json.loads((tmp_path / "out.parts/session.json").read_text())
    assert facts["status"] == "failed" and facts["finalization"]["status"] == "not_started"
    assert not any(e.get("outcome") == "offline" for e in events(tmp_path))
    assert events(tmp_path)[-1]["phase"] == "exhausted"


def test_repeated_dns_errors_are_coalesced_and_never_overwrite_output(tmp_path):
    clock, calls = FakeClock(), []
    def resolve(page):
        calls.append(page)
        if len(calls) == 1:
            return LiveResolution("123", SIGNED)
        raise socket.gaierror(socket.EAI_AGAIN, "DNS")
    def source(url):
        (tmp_path / "out.mp4").write_bytes(b"keep")
        return iter(stream())
    with pytest.raises(OutageCaptureError):
        run_capture(tmp_path, resolve, source, clock=clock,
                    retry_policy=RetryPolicy(window_seconds=100, delays=(1,), max_delay_seconds=1))
    assert len(calls) == 101
    assert len(events(tmp_path)) == 4  # Media close, first resolver error, entry and exhaustion summary.
    assert (tmp_path / "out.mp4").read_bytes() == b"keep"
    assert events(tmp_path)[-1]["retry_attempt"] == 100


def test_cdns_that_fail_despite_same_room_do_not_reset_outage_window(tmp_path):
    clock, source_calls = FakeClock(), []
    def source(url):
        source_calls.append(url)
        if len(source_calls) == 1:
            yield from stream()
        raise ConnectionResetError("reset " + url)
    with pytest.raises(OutageCaptureError) as failure:
        run_capture(tmp_path, lambda _: LiveResolution("123", SIGNED), source, clock=clock,
                    retry_policy=RetryPolicy(window_seconds=4))
    assert len(source_calls) == 3 and len(failure.value.parts) == 1
    assert clock.delays == [1, 2, 1]
    assert "secret" not in json.dumps(events(tmp_path))


@pytest.mark.parametrize("error", [
    PermissionError(errno.EACCES, "denied"), RuntimeError("programming"),
    HTTPError(SIGNED, 403, "denied", {}, None),
])
def test_nonretryable_source_error_fails_once_without_wait(tmp_path, error):
    clock, calls = FakeClock(), []
    def source(url):
        calls.append(url)
        raise error
    with pytest.raises(CaptureError):
        run_capture(tmp_path, lambda _: LiveResolution("123", SIGNED), source, clock=clock)
    assert calls == [SIGNED] and clock.delays == []


def test_writer_permission_failure_is_not_mistaken_for_transport(tmp_path):
    clock, calls = FakeClock(), []
    def writer(tags, directory, **options):
        calls.append(directory)
        raise PermissionError(errno.EACCES, "writer denied")
    with pytest.raises(CaptureError):
        run_capture(tmp_path, lambda _: LiveResolution("123", SIGNED), lambda _: iter(stream()),
                    clock=clock, writer=writer)
    assert len(calls) == 1 and clock.delays == []


def test_retry_after_is_capped_for_source_http_outage(tmp_path):
    clock, calls, sources = FakeClock(), [], []
    def resolve(page):
        calls.append(page)
        if len(calls) == 1:
            return LiveResolution("123", SIGNED)
        raise TikTokOfflineError("offline", status=4)
    def source(url):
        sources.append(url)
        yield from stream()
        raise HTTPError(url, 429, "busy", {"Retry-After": "1000"}, None)
    result = run_capture(tmp_path, resolve, source, clock=clock)
    assert clock.delays == [30] and len(result.parts) == 1


def test_malformed_resolution_after_media_is_not_retried(tmp_path):
    clock, calls = FakeClock(), []
    def resolve(page):
        calls.append(page)
        if len(calls) == 1:
            return LiveResolution("123", SIGNED)
        raise TikTokResolutionError("malformed room")
    with pytest.raises(CaptureError):
        run_capture(tmp_path, resolve, lambda _: iter(stream()), clock=clock)
    assert len(calls) == 2 and clock.delays == [0]


def test_local_ctrl_c_in_patient_wait_preserves_and_finalizes(tmp_path):
    clock, entered = FakeClock(), []
    def notify(status):
        if status["phase"] == "entered":
            entered.append(True)
    def sleep(seconds):
        if entered:
            raise KeyboardInterrupt()
        clock.now += seconds
    clock.sleep = sleep
    calls = []
    def resolve(page):
        calls.append(page)
        if len(calls) == 1:
            return LiveResolution("123", SIGNED)
        raise socket.gaierror("DNS")
    result = run_capture(tmp_path, resolve, lambda _: iter(stream()), clock=clock, recovery_observer=notify)
    assert result.interrupted and len(result.parts) == 1 and (tmp_path / "out.mp4").exists()
