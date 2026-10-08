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
    """Poll complete creator snapshots, adopting configured changes between cycles."""

    def __init__(
        self,
        creators: tuple[str, ...],
        *,
        resolver: Callable[[str], LiveResolution] = resolve_live,
        poll_interval: float = POLL_INTERVAL_SECONDS,
        clock: Callable[[], float] = time.time,
        waiter: Callable[[float], bool] | None = None,
        cycle_completed: Callable[[dict], None] | None = None,
        creator_loader: Callable[[], tuple[str, ...]] | None = None,
        thread_factory: Callable = Thread,
    ) -> None:
        self._creators = validate_monitored_creators(creators)
        if poll_interval <= 0:
            raise ValueError("monitor poll interval must be positive")
        self._resolver = resolver
        self._poll_interval = poll_interval
        self._clock = clock
        self._stop = Event()
        self._waiter = waiter or self._stop.wait
        self._cycle_completed = cycle_completed
        self._creator_loader = creator_loader
        self._thread_factory = thread_factory
        self._configuration_unavailable = False
        self._lock = Lock()
        # Includes the completion callback so a second cycle cannot replace its list.
        self._cycle_lock = Lock()
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
        """Start polling; configured empty lists still check for later additions."""
        if not self._creators and self._creator_loader is None:
            return
        with self._lock:
            if self._thread is not None:
                raise RuntimeError("creator monitor already started")
            self._running = True
            worker = self._thread_factory(target=self._run, name="tikrec-monitor", daemon=False)
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
            snapshot = {
                "poll_interval_seconds": self._poll_interval,
                "running": self._running,
                "cycle_in_progress": self._cycle_in_progress,
                "cycle_count": self._cycle_count,
                "last_cycle_started_at": self._last_cycle_started_at,
                "last_cycle_completed_at": self._last_cycle_completed_at,
                "creators": [dict(self._observations[item]) for item in self._creators],
            }
            if self._creator_loader is not None:
                # Fixed categories expose no config contents, paths or exception text.
                snapshot["configuration"] = {
                    "state": "unavailable" if self._configuration_unavailable else "ok",
                    "reason": "configuration_unavailable" if self._configuration_unavailable else None,
                }
            return snapshot

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
        with self._cycle_lock:
            if self._stop.is_set():
                return
            self._reload_creators()
            if not self._stop.is_set():
                self._observe_cycle()

    def _reload_creators(self) -> None:
        if self._creator_loader is None:
            return
        try:
            # Read outside the status lock: slow/unreadable config cannot block status.
            creators = validate_monitored_creators(self._creator_loader())
        except Exception:
            with self._lock:
                self._configuration_unavailable = True
            return
        with self._lock:
            if self._stop.is_set():
                return
            if creators != self._creators:
                # Replace list and observations together; discard stale LIVE observations.
                self._creators = creators
                self._observations = {item: _observation(item, "pending") for item in creators}
            self._configuration_unavailable = False

    def _observe_cycle(self) -> None:
        started_at = self._clock()
        complete = True
        with self._lock:
            self._cycle_in_progress = True
            self._last_cycle_started_at = started_at
            creators = self._creators
        try:
            for creator in creators:
                if self._stop.is_set():
                    complete = False
                    break
                observation = self._observe(creator)
                with self._lock:
                    self._observations[creator] = observation
        finally:
            # Shutdown during the final resolver also makes this an incomplete cycle.
            complete = complete and not self._stop.is_set()
            completed_at = self._clock()
            with self._lock:
                if complete:
                    self._last_cycle_completed_at = completed_at
                    self._cycle_count += 1
                self._cycle_in_progress = False
        if complete and not self._stop.is_set() and self._cycle_completed is not None:
            try:
                # Policy runs after the published complete snapshot and outside the lock.
                self._cycle_completed(self.snapshot())
            except Exception:
                # One automation failure must not terminate later read-only detection.
                pass

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
