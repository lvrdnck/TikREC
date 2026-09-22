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


def controller_jobs(controller) -> tuple[dict, ...]:
    """Return every current service job while preserving single-controller use."""
    getter = getattr(controller, "jobs", None)
    values = getter() if callable(getter) else (controller.status(),)
    if not isinstance(values, (tuple, list)) or not values:
        raise ValueError("controller jobs unavailable")
    if any(not isinstance(value, dict) for value in values):
        raise ValueError("controller jobs unavailable")
    return tuple(values)


def prior_session_id_for_jobs(jobs: tuple[dict, ...]) -> str | None:
    """Retain the legacy fingerprint only when one prior job is unambiguous."""
    non_idle = [job for job in jobs if job.get("state") != "idle"]
    return prior_session_id(non_idle[0]) if len(non_idle) == 1 else None


def jobs_match_claim(jobs: tuple[dict, ...], claim: PendingAutomaticStart) -> bool:
    """Return whether any independently durable slot proves claim acceptance."""
    return any(job_matches_claim(job, claim) for job in jobs)


def jobs_prove_no_claimed_start(
    jobs: tuple[dict, ...], claim: PendingAutomaticStart,
) -> bool:
    """Clear a claim only when durable slots prove the selected one unchanged."""
    if any(job_matches_claim(job, claim) for job in jobs):
        return False
    if len(jobs) == 1:
        return job_proves_no_claimed_start(jobs[0], claim)
    if claim.previous_session_id is None:
        # A multi-slot claim without a prior identity can only have targeted an
        # idle slot; its continued presence proves the controller did not start.
        return any(job.get("state") == "idle" for job in jobs)
    return any(job.get("session_id") == claim.previous_session_id for job in jobs)


def jobs_match_observation(jobs: tuple[dict, ...], observation: dict) -> bool:
    """Return whether any current slot already owns the observed creator/room."""
    return any(job_matches_observation(job, observation) for job in jobs)


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
    if job.get("active") is not True and job.get("state") in {
        "idle", "completed", "failed",
    }:
        # Settled history cannot re-consume a room after trustworthy offline re-arm.
        return False
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
