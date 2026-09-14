"""Map safe controller snapshots to durable intent without serializing media URLs."""

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
    snapshot = dict(job)
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
    snapshot.update(active=active, part_count=len(sizes),
                    reconnect_count=max(0, resolutions - 1),
                    bytes_written=sum(sizes.values()) + extra,
                    elapsed_seconds=max(0, end - snapshot["started_at"]))
    return snapshot
