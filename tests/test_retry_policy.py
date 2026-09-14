"""No real sleeping: policy stages, caps, elapsed deadline and stop priority."""

from threading import Event

import pytest

from tikrec.capture_control import CaptureControl, CaptureStopped
from tikrec.retry_policy import OutageRecovery, RecoveryExhausted, RetryPolicy


def test_default_schedule_and_server_delay_cap():
    policy = RetryPolicy()
    assert [policy.delay(i) for i in range(1, 9)] == [1, 2, 5, 10, 10, 30, 30, 30]
    assert policy.delay(1, retry_after=1000) == 30
    assert policy.delay(1, retry_after=0) == 1


@pytest.mark.parametrize("options", [
    {"window_seconds": 0}, {"window_seconds": float("inf")}, {"delays": ()},
    {"delays": (0,)}, {"max_delay_seconds": -1}, {"delays": (True,)},
])
def test_invalid_policy_is_rejected(options):
    with pytest.raises(ValueError):
        RetryPolicy(**options)


def test_fake_clock_waits_expire_exactly_at_deadline():
    now, delays = [0.0], []
    def sleep(delay):
        delays.append(delay)
        now[0] += delay
    recovery = OutageRecovery(RetryPolicy(window_seconds=4), clock=lambda: now[0])
    control = CaptureControl(None, sleep)
    for _ in range(2):
        recovery.failure(TimeoutError())
        recovery.wait(control)
    recovery.failure(TimeoutError())
    with pytest.raises(RecoveryExhausted):
        recovery.wait(control)
    assert delays == [1, 2, 1] and now[0] == 4
    recovery.reset()
    assert not recovery.active and recovery.status()["retry_attempt"] == 0


def test_stop_wins_over_expired_deadline_without_sleep():
    event = Event()
    event.set()
    recovery = OutageRecovery(RetryPolicy(), clock=lambda: 0)
    recovery.failure(TimeoutError())
    with pytest.raises(CaptureStopped):
        recovery.wait(CaptureControl(event, lambda _: pytest.fail("must not sleep")))


def test_programming_errors_cannot_enter_policy():
    with pytest.raises(ValueError, match="nonretryable"):
        OutageRecovery(RetryPolicy()).failure(PermissionError("disk"))
