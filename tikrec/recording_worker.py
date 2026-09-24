"""Run one service capture through its final media and manifest mutation."""

from __future__ import annotations

from pathlib import Path

from .live_recovery import OutageCaptureError
from .recording_safety import safe_error


def run_recording_worker(controller, url: str, output_path: Path, recovery=None,
                         expected_room_id: str | None = None) -> None:
    """Finish one capture or resume while its caller holds the writer lease."""
    try:
        options = dict(stop_event=controller._stop, state=controller._state,
                       heartbeat=controller._heartbeat, room_identity=controller._identity,
                       recovery_observer=controller._network_status,
                       retry_policy=controller._retry_policy,
                       recovery_clock=controller._recovery_clock,
                       recovery_waiter=controller._recovery_waiter)
        if controller._job.get("raw_copy_enabled"):
            options["raw_copy_dir"] = controller._parts
        if expected_room_id is not None:
            options.update(controller._automatic_resolvers(expected_room_id))
        if recovery is None:
            result = controller._capture(
                url, parts_directory=controller._parts, output_path=output_path,
                session_id=controller._job["session_id"], **options)
        else:
            result = controller._reconciler.resume(recovery, **options)
    except BaseException as error:
        # A worker failure must leave HTTP threads available and its job durable.
        with controller._lock:
            phase = controller._job["state"]
            controller._job.update(state="failed", error=safe_error(error) or type(error).__name__)
            if isinstance(error, OutageCaptureError):
                controller._job.update(recovery_state="exhausted", recovery_reason="outage_timeout")
                controller._blocked = False
            elif recovery is not None:
                controller._blocked = True
                phase = "finalizing" if phase == "finalizing" else "recovering"
                controller._job.update(state=phase, recovery_state="failed",
                                       recovery_reason="failed_resume")
    else:
        with controller._lock:
            controller._job.update(state="completed", interrupted=result.interrupted,
                                   final_output_path=None if result.output_path is None
                                   else str(result.output_path))
            controller._resolutions = max(controller._resolutions, len(result.connections))
    finally:
        with controller._lock:
            controller._job["ended_at"] = controller._clock()
            try:
                controller._persist()
            except Exception:
                controller._blocked = True
                controller._job.update(recovery_state="failed",
                                       error="could not persist recording result")
            finally:
                controller._active = False
