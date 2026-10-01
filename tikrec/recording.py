"""Own one recording worker independently of terminals and HTTP requests."""

from __future__ import annotations

import time
import uuid
from dataclasses import replace
from collections.abc import Callable
from pathlib import Path
from threading import Event, Lock, Thread

from .automatic_identity import expected_room_resolvers
from .capture import CaptureResult
from .live import capture_live
from .reconciliation import StartupReconciler
from .service_job import (job_snapshot, persist_snapshot, progress_snapshot, update_network_status, update_capture_state)
from .capture_control import CaptureControl
from .retry_policy import RetryPolicy
from .lifecycle_lock import acquire_lifecycle
from .recording_safety import normalize_live_url, safe_error
from .recording_worker import run_recording_worker
from .tiktok_identity import canonical_room_id


class RecordingBusy(ValueError):
    """A recording is already active, or the controller is shutting down."""


class RecordingController:
    """Serialize starts and expose snapshots while capture runs in a worker."""

    def __init__(self, *, capture: Callable[..., CaptureResult] = capture_live,
                 clock: Callable[[], float] = time.time, store=None, reconciler=None,
                 retry_policy=RetryPolicy(), recovery_clock=time.monotonic,
                 recovery_waiter=None, automatic_resolvers=expected_room_resolvers) -> None:
        self._capture = capture
        self._clock = clock
        self._lock = Lock()
        self._stop = Event()
        self._worker: Thread | None = None
        self._active = self._blocked = False
        self._closed = False
        self._job: dict = {"state": "idle"}
        self._parts: Path | None = None
        self._current_part: Path | None = None
        self._current_bytes = 0
        self._resolutions = 0
        self._retry_policy, self._recovery_clock, self._recovery_waiter = retry_policy, recovery_clock, recovery_waiter
        self._automatic_resolvers = automatic_resolvers
        self._store = store
        self._reconciler = reconciler or (StartupReconciler(
            store, clock=clock, save_job=self._save_recovery, should_stop=self._user_stop)
            if store else None)
        if reconciler is not None:
            reconciler.save_job = self._save_recovery
            reconciler.should_stop = self._user_stop
        if store is not None:
            try:
                saved = store.load()
            except Exception:
                self._blocked = True
                self._job = {"state": "recovering", "recovery_state": "failed",
                             "recovery_reason": "ambiguous_state",
                             "error": "invalid durable state; preserve artifacts"}
            else:
                if saved is not None:
                    self._job = job_snapshot(saved)
                    self._parts = Path(saved.parts_directory)
                    if saved.needs_reconciliation:
                        # Reserve recovery before exposing this controller to HTTP handlers.
                        self._active = self._blocked = True
                        self._job.update(state="reconciling", recovery_state="reconciling")
                        self._worker = Thread(target=self._recover, name="tikrec-recovery", daemon=False)
                        try:
                            self._worker.start()
                        except Exception:
                            self._active = False
                            self._worker = None
                            self._job.update(state="recovering", recovery_state="failed",
                                             error="could not start recovery worker")

    def health(self) -> dict:
        """Report whether the service can accept another recording."""
        from . import __version__

        with self._lock:
            return {"service": "tikrec", "version": __version__,
                    "available": not self._active and not self._closed and not self._blocked,
                    "active": self._active, "shutting_down": self._closed,
                    "recovery_state": self._job.get("recovery_state"),
                    "recovery_reason": self._job.get("recovery_reason")}

    def status(self) -> dict:
        """Return current progress or the most recent result, without CDN URLs."""
        with self._lock:
            return self._snapshot()

    def ownership(self) -> dict:
        """Return current identity and local paths under the controller lock."""
        with self._lock:
            return {"current": bool((self._active or self._blocked) and self._job.get("session_id")),
                    "session_id": self._job.get("session_id"), "source_url": self._job.get("source_url"),
                    "room_id": self._job.get("room_id"), "output_path": self._job.get("output_path"),
                    "parts_directory": self._job.get("parts_directory")}

    def start(self, url: str, output: str, *, raw_copy: bool = False,
              expected_room_id: str | None = None) -> dict:
        """Accept one job and launch it independently of the requesting connection."""
        url = normalize_live_url(url)
        if expected_room_id is not None:
            expected_room_id = canonical_room_id(expected_room_id)
        output_path = Path(output)
        if type(raw_copy) is not bool:
            raise ValueError("raw_copy must be a boolean")
        if not output or "\x00" in output or not output_path.is_absolute():
            raise ValueError("output must be an absolute path on the service machine")
        if output_path.suffix.lower() != ".mp4":
            raise ValueError("output must have an .mp4 extension")
        with self._lock:
            if self._active or self._closed or self._blocked:
                raise RecordingBusy("recording active, recovery unresolved, or service shutting down")
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
                "room_id": None, "resumed": False, "resume_count": 0,
                "recovery_state": None, "recovery_reason": None, "raw_copy_enabled": raw_copy,
            }
            self._worker = Thread(target=self._run, args=(url, output_path),
                                  kwargs={"expected_room_id": expected_room_id},
                                  name="tikrec-recording", daemon=False)
            try:
                self._persist()
                # Reserve the slot before starting; concurrent HTTP starts see it immediately.
                self._worker.start()
            except Exception:
                self._active = False
                self._worker = None
                self._job.update(state="failed", error="could not start recording worker",
                                 ended_at=self._clock())
                self._persist()
                raise RuntimeError("could not start recording worker") from None
            return self._snapshot()

    def stop(self) -> dict:
        """Request cooperative stop, including during resolution or reconnect."""
        with self._lock:
            if (self._active or self._blocked) and self._parts is not None:
                self._job["stop_requested"] = True
                self._persist()
                self._stop.set()
            # Repeated stop is harmless, including while the finalizer is already running.
            return self._snapshot()

    def shutdown(self) -> None:
        """Reject new jobs, stop capture, and wait for safe finalization to finish."""
        with self._lock:
            self._closed = True
            if self._active:
                self._job["stop_requested"] = True
                self._persist()
            # Inactive deferred recovery preserves intent for the next startup assessment.
            self._stop.set()
            worker = self._worker
        if worker is not None:
            # Never join under the lock: the worker needs it to publish its final result.
            worker.join()

    def _state(self, state: str) -> None:
        with self._lock:
            if state == "resolving":
                self._resolutions += 1
            if update_capture_state(self._job, state):
                self._persist()

    def _heartbeat(self, path: Path, byte_count: int) -> None:
        with self._lock:
            self._current_part = path
            self._current_bytes = byte_count

    def _run(self, url: str, output_path: Path, recovery=None,
             expected_room_id: str | None = None) -> None:
        try:
            with acquire_lifecycle(output_path.parent, "writer"):
                run_recording_worker(self, url, output_path, recovery, expected_room_id)
        except BaseException as error:
            # Keep a failed lease acquisition as a visible worker failure.
            with self._lock:
                self._job.update(state="failed", error=safe_error(error) or type(error).__name__)
                self._blocked = recovery is not None
                self._job["ended_at"] = self._clock()
                try:
                    self._persist()
                except Exception:
                    self._blocked = True
                self._active = False

    def _persist(self):
        if self._store is not None:
            persist_snapshot(self._store, self._job)

    def _identity(self, room_id):
        with self._lock:
            if self._job["room_id"] is None:
                self._job["room_id"] = room_id
                self._persist()

    def _recovery_observed(self, job):
        with self._lock:
            stopped = self._job.get("stop_requested", False) or job.stop_requested
            self._job.update(job_snapshot(job), recovery_state=job.state, stop_requested=stopped)

    def _save_recovery(self, job):
        with self._lock:
            if self._job.get("stop_requested"):
                job = replace(job, stop_requested=True)
                if job.state == "resuming":
                    # A stop arriving during resolution wins over the pending resume decision.
                    job = replace(job, state="finalizing", resume_count=self._job["resume_count"],
                                  recovery_reason="user_stop")
            self._store.save(job)
            return job

    def _user_stop(self):
        with self._lock:
            return self._job.get("stop_requested", False)

    def _network_status(self, status):
        with self._lock:
            update_network_status(self._job, status, clock=self._recovery_clock)
            if status["phase"] in {"entered", "recovered", "offline", "live_changed", "user_stop"}:
                self._persist()

    def _recover(self):
        try:
            with acquire_lifecycle(Path(self._job["output_path"]).parent, "writer"):
                self._recover_locked()
        except BaseException:
            with self._lock:
                self._active = False
                self._blocked = True
                self._job.update(state="recovering", recovery_state="failed",
                                 recovery_reason="ambiguous_state", error="startup recovery failed")

    def _recover_locked(self):
        try:
            result = self._reconciler.reconcile(observe=self._recovery_observed,
                retry_policy=self._retry_policy, recovery_clock=self._recovery_clock,
                control=CaptureControl(self._stop, time.sleep, waiter=self._recovery_waiter),
                recovery_observer=self._network_status)
            with self._lock:
                if result.job is not None:
                    stopped = self._job.get("stop_requested", False) or result.job.stop_requested
                    self._job.update(job_snapshot(result.job), stop_requested=stopped)
                self._blocked = result.blocked
                if result.blocked:
                    self._job.update(state="recovering", recovery_state=result.outcome,
                                     recovery_reason=result.reason, error=result.error or "startup recovery failed")
                self._active = result.outcome == "resume"
                if result.outcome == "exhausted":
                    self._job.update(recovery_state="exhausted", error=result.error)
            if result.outcome == "resume":
                self._run(result.job.source_url, Path(result.job.output_path), recovery=result)
        except BaseException:
            with self._lock:
                self._active = False
                self._blocked = True
                self._job.update(state="recovering", recovery_state="failed",
                                 recovery_reason="ambiguous_state", error="startup recovery failed")

    def _snapshot(self) -> dict:
        return progress_snapshot(self._job, parts=self._parts, active=self._active,
                                 current_part=self._current_part, current_bytes=self._current_bytes,
                                 resolutions=self._resolutions, clock=self._clock)
