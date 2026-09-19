"""Map safe controller snapshots to durable intent without serializing media URLs."""

import json
import os
from pathlib import Path

from .job_state import JobState


def default_job_state_path() -> Path:
    """Use a stable per-user location independent of Task Scheduler working directory."""
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        base = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state"))
    return base / "TikREC" / "job.json"


def job_snapshot(job: JobState) -> dict:
    """Restore safe API fields; media progress remains derived from session storage."""
    return {"state": job.state, "session_id": job.session_id, "source_url": job.source_url,
            "started_at": job.started_at, "ended_at": job.ended_at,
            "output_path": job.output_path, "parts_directory": job.parts_directory,
            "stop_requested": job.stop_requested, "room_id": job.room_id,
            "resume_count": job.resume_count, "resumed": job.resume_count > 0,
            "recovery_state": None, "recovery_reason": job.recovery_reason,
            "final_output_path": job.output_path if job.finalization_completed else None,
            "interrupted": job.stop_requested, "error": None}


def persist_snapshot(store, snapshot):
    """Atomically publish only the job schema's allowlisted intent fields."""
    values = {name: snapshot[name] for name in JobState.__dataclass_fields__ if name in snapshot}
    values["finalization_completed"] = snapshot.get("final_output_path") is not None
    store.save(JobState(**values))


def progress_snapshot(job, *, parts, active, current_part, current_bytes, resolutions, clock):
    """Derive safe retained-byte progress while surviving concurrent filesystem changes."""
    snapshot = {k: v for k, v in job.items() if not k.startswith("_")}
    if job.get("recovery_state") == "recovery_wait":
        # Status countdowns are derived in memory, never saved every second.
        now = job["_recovery_clock"]()
        snapshot["next_retry_in_seconds"] = max(0.0, job["_next_retry_at"] - now)
        snapshot["outage_elapsed_seconds"] += max(0.0, now - job["_outage_observed_at"])
    if parts is None:
        return {**snapshot, "active": False}
    sizes = {}
    try:
        for path in parts.glob("part-*.flv"):
            sizes[path] = path.stat().st_size
    except OSError:
        # A status read must survive disk trouble while capture reports its own failure.
        pass
    extra = current_bytes if active and current_part not in sizes else 0
    end = snapshot["ended_at"] if snapshot["ended_at"] is not None else clock()
    # Never hold the manifest open against its Windows atomic replacement.
    # Once capture is inactive, it keeps allocation counts across restarts.
    reconnects = max(0, resolutions - 1)
    if not active:
        reconnects = max(reconnects, _manifest_reconnect_count(parts))
    snapshot.update(active=active, part_count=len(sizes),
                    reconnect_count=reconnects,
                    bytes_written=sum(sizes.values()) + extra,
                    elapsed_seconds=max(0, end - snapshot["started_at"]))
    return snapshot


def _manifest_reconnect_count(parts):
    try:
        document = json.loads((parts / "session.json").read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return 0
    value = document.get("reconnect_count") if isinstance(document, dict) else None
    return value if type(value) is int and value >= 0 else 0


def update_network_status(job, status, *, clock):
    """Apply safe outage progress while keeping volatile countdown clocks out of persistence."""
    phase = status["phase"]
    job.update({k: v for k, v in status.items() if k != "phase"})
    now = clock()
    job.update(_recovery_clock=clock, _next_retry_at=now + status["next_retry_in_seconds"],
               _outage_observed_at=now)
    if phase in {"entered", "wait"}:
        job.update(state="recovering_network", recovery_state="recovery_wait", recovery_reason="network_outage")
    elif phase == "recovered":
        job.update(recovery_state=None, recovery_reason="network_recovered", next_retry_in_seconds=0)
    elif phase in {"offline", "live_changed", "user_stop"}:
        job.update(recovery_state=None, next_retry_in_seconds=0,
                   recovery_reason={"offline": "room_ended", "live_changed": "live_changed",
                                    "user_stop": "user_stop"}[phase])
    elif phase == "exhausted":
        job.update(recovery_state="exhausted", recovery_reason="outage_timeout", next_retry_in_seconds=0)
    elif phase == "failed":
        job.update(recovery_state="failed", recovery_reason=None, next_retry_in_seconds=0)


def update_capture_state(job, state):
    """Keep resolver attempts visibly recovering while persisting only real phase changes."""
    if state == "resolving" and job.get("recovery_state") == "recovery_wait":
        # A DNS retry is still the same outage, not a new durable capture phase.
        state = "recovering_network"
    changed = job["state"] != state
    job["state"] = state
    if state == "recording":
        job["recovery_state"] = None
    return changed
