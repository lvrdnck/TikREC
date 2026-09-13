"""Own one recording worker independently of terminals and HTTP requests."""

from __future__ import annotations

import re
import time
import uuid
from collections.abc import Callable
from pathlib import Path
from threading import Event, Lock, Thread
from urllib.parse import urlsplit

from .capture import CaptureResult
from .live import capture_live


class RecordingBusy(ValueError):
    """A recording is already active, or the controller is shutting down."""


def normalize_live_url(url: str) -> str:
    """Accept a public LIVE page and discard query/fragment metadata."""
    parsed = urlsplit(url)
    if (parsed.scheme not in {"http", "https"}
            or parsed.hostname not in {"tiktok.com", "www.tiktok.com"}
            or parsed.netloc not in {"tiktok.com", "www.tiktok.com"}
            or not re.fullmatch(r"/@[A-Za-z0-9_.]+/live/?", parsed.path)):
        raise ValueError("provide a public https://www.tiktok.com/@username/live URL")
    # Only the known public host reaches the resolver; callers cannot supply a CDN URL.
    return "https://www.tiktok.com" + parsed.path.rstrip("/")


def safe_error(error: BaseException) -> str:
    """Return a bounded single-line summary with ephemeral URLs removed."""
    return " ".join(re.sub(r"https?://\S+", "[URL redacted]", str(error)).split())[:500]


class RecordingController:
    """Serialize starts and expose snapshots while capture runs in a worker."""

    def __init__(self, *, capture: Callable[..., CaptureResult] = capture_live,
                 clock: Callable[[], float] = time.time) -> None:
        self._capture = capture
        self._clock = clock
        self._lock = Lock()
        self._stop = Event()
        self._worker: Thread | None = None
        self._active = False
        self._closed = False
        self._job: dict = {"state": "idle"}
        self._parts: Path | None = None
        self._current_part: Path | None = None
        self._current_bytes = 0
        self._resolutions = 0

    def health(self) -> dict:
        """Report whether the service can accept another recording."""
        from . import __version__

        with self._lock:
            return {"service": "tikrec", "version": __version__,
                    "available": not self._active and not self._closed,
                    "active": self._active, "shutting_down": self._closed}

    def status(self) -> dict:
        """Return current progress or the most recent result, without CDN URLs."""
        with self._lock:
            return self._snapshot()

    def start(self, url: str, output: str) -> dict:
        """Accept one job and launch it independently of the requesting connection."""
        url = normalize_live_url(url)
        output_path = Path(output)
        if not output or "\x00" in output or not output_path.is_absolute():
            raise ValueError("output must be an absolute path on the service machine")
        if output_path.suffix.lower() != ".mp4":
            raise ValueError("output must have an .mp4 extension")
        with self._lock:
            if self._active or self._closed:
                raise RecordingBusy("recording already active or service shutting down")
            self._parts = output_path.with_name(f"{output_path.stem}.parts")
            if output_path.exists() or self._parts.exists():
                raise ValueError("output or retained parts already exist; choose a new output")
            self._stop = Event()
            self._active = True
            self._current_part = None
            self._current_bytes = self._resolutions = 0
            self._job = {
                "state": "resolving", "session_id": str(uuid.uuid4()),
                "source_url": url, "started_at": self._clock(), "ended_at": None,
                "output_path": str(output_path), "final_output_path": None,
                "parts_directory": str(self._parts), "stop_requested": False,
                "interrupted": False, "error": None,
            }
            self._worker = Thread(target=self._run, args=(url, output_path),
                                  name="tikrec-recording", daemon=False)
            try:
                # Reserve the slot before starting; concurrent HTTP starts see it immediately.
                self._worker.start()
            except Exception:
                self._active = False
                self._worker = None
                self._job.update(state="failed", error="could not start recording worker",
                                 ended_at=self._clock())
                raise RuntimeError("could not start recording worker") from None
            return self._snapshot()

    def stop(self) -> dict:
        """Request cooperative stop, including during resolution or reconnect."""
        with self._lock:
            if self._active:
                self._job["stop_requested"] = True
                self._stop.set()
            # Repeated stop is harmless, including while the finalizer is already running.
            return self._snapshot()

    def shutdown(self) -> None:
        """Reject new jobs, stop capture, and wait for safe finalization to finish."""
        with self._lock:
            self._closed = True
            self._stop.set()
            if self._active:
                self._job["stop_requested"] = True
            worker = self._worker
        if worker is not None:
            # Never join under the lock: the worker needs it to publish its final result.
            worker.join()

    def _state(self, state: str) -> None:
        with self._lock:
            self._job["state"] = state
            if state == "resolving":
                self._resolutions += 1

    def _heartbeat(self, path: Path, byte_count: int) -> None:
        with self._lock:
            self._current_part = path
            self._current_bytes = byte_count

    def _run(self, url: str, output_path: Path) -> None:
        try:
            result = self._capture(
                url, parts_directory=self._parts, output_path=output_path,
                stop_event=self._stop, state=self._state, heartbeat=self._heartbeat,
                session_id=self._job["session_id"],
            )
        except BaseException as error:
            # Contain even an injected worker interrupt; HTTP threads must remain available.
            with self._lock:
                self._job.update(state="failed", error=safe_error(error) or type(error).__name__)
        else:
            with self._lock:
                self._job.update(state="completed", interrupted=result.interrupted,
                                 final_output_path=None if result.output_path is None
                                 else str(result.output_path))
                self._resolutions = max(self._resolutions, len(result.connections))
        finally:
            with self._lock:
                self._job["ended_at"] = self._clock()
                self._active = False

    def _snapshot(self) -> dict:
        snapshot = dict(self._job)
        if self._parts is None:
            return {**snapshot, "active": False}
        sizes = {}
        try:
            for path in self._parts.glob("part-*.flv"):
                sizes[path] = path.stat().st_size
        except OSError:
            # A status read must survive disk trouble while capture reports its own failure.
            pass
        extra = self._current_bytes if self._active and self._current_part not in sizes else 0
        end = snapshot["ended_at"] if snapshot["ended_at"] is not None else self._clock()
        snapshot.update(active=self._active, part_count=len(sizes),
                        reconnect_count=max(0, self._resolutions - 1),
                        bytes_written=sum(sizes.values()) + extra,
                        elapsed_seconds=max(0, end - snapshot["started_at"]))
        return snapshot
