"""Read-only background observation of explicitly configured public creators."""

from __future__ import annotations

import time
from collections.abc import Callable
from threading import Event, Lock, Thread

from .creator_identity import validate_monitored_creators
from .tiktok import (TikTokOfflineError, TikTokResolutionError,
                     TikTokResolutionTransientError, resolve_live)
from .tiktok_identity import LiveResolution


POLL_INTERVAL_SECONDS = 30.0


class CreatorMonitor:
    """Poll one immutable creator list and publish sanitized in-memory snapshots."""

    def __init__(
        self,
        creators: tuple[str, ...],
        *,
        resolver: Callable[[str], LiveResolution] = resolve_live,
        poll_interval: float = POLL_INTERVAL_SECONDS,
        clock: Callable[[], float] = time.time,
        waiter: Callable[[float], bool] | None = None,
    ) -> None:
        self._creators = validate_monitored_creators(creators)
        if poll_interval <= 0:
            raise ValueError("monitor poll interval must be positive")
        self._resolver = resolver
        self._poll_interval = poll_interval
        self._clock = clock
        self._stop = Event()
        self._waiter = waiter or self._stop.wait
        self._lock = Lock()
        self._thread: Thread | None = None
        self._running = False
        self._cycle_in_progress = False
        self._cycle_count = 0
        self._last_cycle_started_at: float | None = None
        self._last_cycle_completed_at: float | None = None
        self._observations = {
            creator: _observation(creator, "pending") for creator in self._creators
        }

    def start(self) -> None:
        """Start one polling worker, or remain idle for an empty creator list."""
        if not self._creators:
            return
        with self._lock:
            if self._thread is not None:
                raise RuntimeError("creator monitor already started")
            self._running = True
            worker = Thread(target=self._run, name="tikrec-monitor", daemon=False)
            self._thread = worker
        try:
            worker.start()
        except BaseException:
            with self._lock:
                self._running = False
                self._thread = None
            raise

    def stop(self) -> None:
        """Request cooperative polling shutdown and wake the interval wait."""
        self._stop.set()

    def join(self) -> None:
        """Wait for a started polling worker to finish its current resolver call."""
        with self._lock:
            worker = self._thread
        if worker is not None:
            worker.join()

    def shutdown(self) -> None:
        """Request shutdown and wait for the monitoring worker."""
        self.stop()
        self.join()

    def snapshot(self) -> dict:
        """Return a thread-safe JSON-safe copy without transport URLs or secrets."""
        with self._lock:
            return {
                "poll_interval_seconds": self._poll_interval,
                "running": self._running,
                "cycle_in_progress": self._cycle_in_progress,
                "cycle_count": self._cycle_count,
                "last_cycle_started_at": self._last_cycle_started_at,
                "last_cycle_completed_at": self._last_cycle_completed_at,
                "creators": [dict(self._observations[item]) for item in self._creators],
            }

    def _run(self) -> None:
        try:
            while not self._stop.is_set():
                self._poll_cycle()
                # The interval begins only after every attempted observation completes.
                if self._waiter(self._poll_interval):
                    break
        finally:
            with self._lock:
                self._running = False
                self._cycle_in_progress = False

    def _poll_cycle(self) -> None:
        started_at = self._clock()
        with self._lock:
            self._cycle_in_progress = True
            self._last_cycle_started_at = started_at
        try:
            for creator in self._creators:
                if self._stop.is_set():
                    break
                observation = self._observe(creator)
                with self._lock:
                    self._observations[creator] = observation
        finally:
            completed_at = self._clock()
            with self._lock:
                self._last_cycle_completed_at = completed_at
                self._cycle_count += 1
                self._cycle_in_progress = False

    def _observe(self, creator: str) -> dict:
        page = f"https://www.tiktok.com/@{creator}/live"
        try:
            resolution = self._resolver(page)
            if not isinstance(resolution, LiveResolution):
                return _observation(
                    creator, "unknown", self._clock(), reason="unverifiable"
                )
            # Copy only canonical identity; the signed transport URL dies with this scope.
            return _observation(
                creator, "live", self._clock(), room_id=resolution.room_id
            )
        except TikTokOfflineError:
            return _observation(creator, "offline", self._clock())
        except TikTokResolutionTransientError:
            return _observation(creator, "unknown", self._clock(), reason="transient")
        except TikTokResolutionError:
            return _observation(creator, "unknown", self._clock(), reason="unverifiable")
        except Exception:
            return _observation(creator, "unknown", self._clock(), reason="unexpected")


def _observation(
    creator: str,
    state: str,
    observed_at: float | None = None,
    *,
    room_id: str | None = None,
    reason: str | None = None,
) -> dict:
    return {
        "creator": creator,
        "state": state,
        "observed_at": observed_at,
        "room_id": room_id,
        "unknown_reason": reason,
    }
