"""Compare safe controller job facts during automatic-start reconciliation."""

from uuid import UUID

from .automation_state import PendingAutomaticStart
from .tiktok_identity import canonical_room_id


def prior_session_id(job: dict) -> str | None:
    """Return the safe inactive job fingerprint recorded before a claim."""
    if job.get("state") == "idle":
        return None
    value = job.get("session_id")
    if not isinstance(value, str):
        raise ValueError("controller job identity unavailable")
    try:
        canonical = str(UUID(value))
    except ValueError:
        raise ValueError("controller job identity unavailable") from None
    if value != canonical:
        raise ValueError("controller job identity unavailable")
    return value


def job_matches_claim(job: dict, claim: PendingAutomaticStart) -> bool:
    """Return whether the latest durable job proves claim acceptance."""
    page = f"https://www.tiktok.com/@{claim.creator}/live"
    return (
        job.get("source_url") == page
        and job.get("output_path") == claim.output_path
        and job.get("parts_directory") == claim.parts_directory
    )


def job_proves_no_claimed_start(job: dict, claim: PendingAutomaticStart) -> bool:
    """Return whether durable job state is unchanged from before the claim."""
    if claim.previous_session_id is None:
        return job.get("state") == "idle"
    return job.get("session_id") == claim.previous_session_id


def job_matches_observation(job: dict, observation: dict) -> bool:
    """Return whether an existing job owns this creator and observed room."""
    creator = observation.get("creator")
    try:
        room_id = canonical_room_id(observation.get("room_id"))
        saved_room = canonical_room_id(job.get("room_id"))
    except (TypeError, ValueError):
        return False
    return (
        room_id == saved_room
        and job.get("source_url") == f"https://www.tiktok.com/@{creator}/live"
    )
