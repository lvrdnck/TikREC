"""Coalesced outage boundaries beside existing numbered connection evidence."""

from .connection_log import _append_jsonl_record
from .job_state import _timestamp


PHASES = {"entered", "recovered", "exhausted", "offline", "live_changed", "user_stop", "failed"}
KINDS = {"dns", "timeout", "connection", "http", "network"}


def append_network_record(path, *, timestamp, session_id, phase, recovery):
    """Append one episode boundary, summarizing repeated failures rather than every wait."""
    status = recovery.status()
    record = {"event": "network_recovery", "timestamp": timestamp, "session_id": session_id,
              "phase": phase, "retry_attempt": status["retry_attempt"],
              "outage_elapsed_seconds": status["outage_elapsed_seconds"],
              "failure_kind": status["network_failure_kind"]}
    validate_network_record(record, session_id)
    _append_jsonl_record(path, record)


def validate_network_record(record, identity):
    """Reject malformed/covert transport fields before later session continuation."""
    if (set(record) != {"event", "timestamp", "session_id", "phase", "retry_attempt",
                       "outage_elapsed_seconds", "failure_kind"}
            or record["event"] != "network_recovery" or record["session_id"] != identity
            or record["phase"] not in PHASES or record["failure_kind"] not in KINDS
            or not _timestamp(record["timestamp"]) or not _timestamp(record["outage_elapsed_seconds"])
            or type(record["retry_attempt"]) is not int or record["retry_attempt"] < 1):
        raise ValueError("invalid network recovery evidence")
