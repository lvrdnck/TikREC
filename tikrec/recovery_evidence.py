"""Fixed, non-secret service reconciliation evidence appended to connection logs."""

from .connection_log import _append_jsonl_record
from .job_state import _timestamp


RECOVERY_REASONS = {"process_restart", "room_ended", "live_changed", "user_stop",
                    "recovery_finalization", "existing_output", "identity_unavailable",
                    "ambiguous_state", "failed_resume"}


def append_recovery_record(path, *, timestamp, session_id, reason, resume_count):
    """Record only observed restart decisions, never an inferred crash timestamp."""
    record = {"event": "service_recovery", "timestamp": timestamp,
              "session_id": session_id, "reason": reason, "resume_count": resume_count}
    validate_recovery_record(record, session_id)
    _append_jsonl_record(path, record)


def validate_recovery_record(record, session_id):
    """Reject malformed service boundaries before appending new media evidence."""
    if (set(record) != {"event", "timestamp", "session_id", "reason", "resume_count"}
            or record["event"] != "service_recovery"
            or record["session_id"] != session_id
            or not _timestamp(record["timestamp"])
            or record["reason"] not in RECOVERY_REASONS
            or type(record["resume_count"]) is not int or record["resume_count"] < 0):
        raise ValueError("invalid service recovery evidence")
