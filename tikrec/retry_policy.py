"""One deterministic bounded patient-outage policy for LIVE and startup recovery."""

import math
import time
from dataclasses import dataclass

from .network_errors import classify_failure


DEFAULT_RECOVERY_WINDOW_SECONDS = 900


class RecoveryExhausted(RuntimeError):
    """The outage window expired without usable capture continuation or room end."""


@dataclass(frozen=True)
class RetryPolicy:
    """Internal configuration: 15 minutes, staged positive waits capped at 30 seconds."""

    window_seconds: float = DEFAULT_RECOVERY_WINDOW_SECONDS
    delays: tuple[float, ...] = (1.0, 2.0, 5.0, 10.0, 10.0, 30.0)
    max_delay_seconds: float = 30.0

    def __post_init__(self):
        values = (self.window_seconds, self.max_delay_seconds, *self.delays)
        if not self.delays or any(type(v) not in {int, float} or not math.isfinite(v) or v <= 0
                                  for v in values):
            raise ValueError("retry policy requires finite positive window and delays")

    def delay(self, attempt, *, retry_after=None):
        """Select the staged delay, applying a bounded Retry-After as a minimum."""
        if type(attempt) is not int or attempt < 1:
            raise ValueError("retry attempt must be a positive integer")
        delay = self.delays[min(attempt, len(self.delays)) - 1]
        if type(retry_after) in {int, float} and math.isfinite(retry_after) and retry_after >= 0:
            delay = max(delay, retry_after)
        return min(delay, self.max_delay_seconds)


class OutageRecovery:
    """Track one contiguous failure episode using an injected monotonic clock."""

    def __init__(self, policy, *, clock=time.monotonic, wall_clock=time.time):
        self.policy, self.clock, self.wall_clock = policy, clock, wall_clock
        self.started = None
        self.attempt = 0
        self.reason = "network"
        self.delay_seconds = 0.0

    @property
    def active(self):
        """Identify an unsettled outage episode."""
        return self.started is not None

    def failure(self, error, *, transport=False):
        """Count only a classified transient error; reject arbitrary local failures."""
        failure = classify_failure(error, transport=transport, now=self.wall_clock())
        if failure.category != "transient":
            raise ValueError("nonretryable failure cannot enter outage recovery")
        if self.started is None:
            self.started = self.clock()
        self.attempt += 1
        self.reason = failure.reason
        self.delay_seconds = self.policy.delay(self.attempt, retry_after=failure.retry_after)

    def status(self):
        """Return bounded, non-secret retry progress without persistence churn."""
        elapsed = max(0.0, self.clock() - self.started) if self.active else 0.0
        remaining = max(0.0, self.policy.window_seconds - elapsed)
        return {"retry_attempt": self.attempt, "next_retry_in_seconds": min(self.delay_seconds, remaining),
                "outage_elapsed_seconds": elapsed, "recovery_window_seconds": self.policy.window_seconds,
                "network_failure_kind": self.reason}

    def wait(self, control):
        """Wake on user stop and check the deadline before another network attempt."""
        control.check()
        status = self.status()
        if status["outage_elapsed_seconds"] >= self.policy.window_seconds:
            raise RecoveryExhausted("patient recovery window exhausted; room end is unproven")
        control.wait(status["next_retry_in_seconds"])
        if self.status()["outage_elapsed_seconds"] >= self.policy.window_seconds:
            raise RecoveryExhausted("patient recovery window exhausted; room end is unproven")

    def reset(self):
        """Begin a new episode only after prior recovery proved useful progress."""
        self.started, self.attempt, self.delay_seconds = None, 0, 0.0
