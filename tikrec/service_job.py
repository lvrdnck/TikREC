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
