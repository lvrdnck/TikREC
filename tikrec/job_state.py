"""Persist one explicitly started service job, separate from media evidence."""

from __future__ import annotations

import json
import math
import os
import re
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile

from .tiktok_identity import canonical_room_id


JOB_SCHEMA_VERSION = 1
_CAPTURE_STATES = {"resolving", "recovering", "reconciling", "resuming",
                   "recording", "reconnecting", "recovering_network", "recovery_wait"}
_TERMINAL_STATES = {"completed", "failed"}
_REASONS = {None, "process_restart", "user_stop", "room_ended", "live_changed",
            "identity_unavailable", "recovery_finalization", "existing_output",
            "failed_resume", "ambiguous_state", "unusable_media", "network_outage",
            "network_recovered", "outage_timeout"}
_PUBLIC_PAGE = re.compile(r"https://www\.tiktok\.com/@[A-Za-z0-9_.]+/live")


class JobStateError(ValueError):
    """Durable intent is unsupported or ambiguous; retain artifacts unchanged."""


@dataclass(frozen=True)
class JobState:
    """Non-secret intent for the latest explicit recording; no media facts."""

    session_id: str
    source_url: str
    output_path: str
    parts_directory: str
    started_at: float
    schema_version: int = JOB_SCHEMA_VERSION
    state: str = "resolving"
    ended_at: float | None = None
    stop_requested: bool = False
    finalization_completed: bool = False
    room_id: str | None = None
    resume_count: int = 0
    recovery_reason: str | None = None

    @property
    def needs_reconciliation(self) -> bool:
        """Identify interrupted work, including a stopped job awaiting finalization."""
        return self.state not in _TERMINAL_STATES and not self.finalization_completed

    @property
    def may_resume(self) -> bool:
        """Allow identity verification only; callers must still prove the same LIVE."""
        # A URL names an account, so only a saved room ID can anchor automatic resume.
        return (self.needs_reconciliation and self.state in _CAPTURE_STATES
                and not self.stop_requested and self.room_id is not None)

    def validate(self) -> None:
        """Reject unsafe or ambiguous fields before reading or publishing intent."""
        try:
            valid = (
                type(self.schema_version) is int and self.schema_version == JOB_SCHEMA_VERSION
                and isinstance(self.session_id, str)
                and str(uuid.UUID(self.session_id)) == self.session_id
                and isinstance(self.source_url, str)
                and _PUBLIC_PAGE.fullmatch(self.source_url) is not None
                and _absolute_path(self.output_path) and _absolute_path(self.parts_directory)
                and Path(self.output_path).suffix.lower() == ".mp4"
                and Path(self.parts_directory) == Path(self.output_path).with_name(
                    f"{Path(self.output_path).stem}.parts")
                and _timestamp(self.started_at)
                and (self.ended_at is None or
                     (_timestamp(self.ended_at) and self.ended_at >= self.started_at))
                and self.state in _CAPTURE_STATES | _TERMINAL_STATES | {"finalizing"}
                and (self.state not in _TERMINAL_STATES or self.ended_at is not None)
                and type(self.stop_requested) is bool
                and type(self.finalization_completed) is bool
                and type(self.resume_count) is int and self.resume_count >= 0
                and (self.room_id is None or
                     (isinstance(self.room_id, str) and
                      canonical_room_id(self.room_id) == self.room_id))
                and self.recovery_reason in _REASONS
            )
        except (ValueError, TypeError, AttributeError, OverflowError):
            valid = False
        if not valid:
            # Fixed diagnostics cannot reflect corrupt values containing tokens or CDN URLs.
            raise JobStateError("invalid durable job state; preserve artifacts")


class JobStateStore:
    """Atomically store one job for a single owning service process.

    This file records intent before a worker can create session.json. It never
    substitutes for inspection of the manifest, parts, or final output.
    """

    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def load(self) -> JobState | None:
        """Load committed intent only; absence is idle, corrupt intent is an error."""
        try:
            with self.path.open("r", encoding="utf-8") as handle:
                values = json.load(handle, object_pairs_hook=_unique_fields)
        except FileNotFoundError:
            return None
        except (UnicodeError, ValueError):
            raise JobStateError("invalid durable job state; preserve artifacts") from None
        try:
            # Missing stop/identity flags must not silently acquire permissive defaults.
            if not isinstance(values, dict) or set(values) != set(JobState.__dataclass_fields__):
                raise ValueError("unexpected fields")
            job = JobState(**values)
            job.validate()
        except (TypeError, ValueError):
            raise JobStateError("invalid durable job state; preserve artifacts") from None
        return job

    def save(self, job: JobState) -> None:
        """Flush complete intent before replacement; propagate storage failure."""
        job.validate()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary: Path | None = None
        try:
            # Unique exclusive files avoid consuming or deleting evidence from a prior crash.
            with NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.path.parent,
                                    prefix=f".{self.path.name}.", suffix=".partial",
                                    delete=False) as handle:
                temporary = Path(handle.name)
                json.dump(asdict(job), handle, indent=2, sort_keys=True, allow_nan=False)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            # Close before promotion because Windows disallows renaming an open temp file.
            os.replace(temporary, self.path)
            if os.name != "nt":
                # POSIX requires syncing the directory to durably publish its new entry.
                descriptor = os.open(self.path.parent, os.O_RDONLY)
                try:
                    os.fsync(descriptor)
                finally:
                    os.close(descriptor)
        finally:
            if temporary is not None:
                # Only this attempt's temporary file is eligible for normal error cleanup.
                temporary.unlink(missing_ok=True)


def _absolute_path(value: object) -> bool:
    return (isinstance(value, str) and "\x00" not in value and
            "://" not in value and Path(value).is_absolute())


def _timestamp(value: object) -> bool:
    # bool is an int subclass, but true/false cannot be lifecycle timestamps.
    return type(value) in {int, float} and math.isfinite(value) and value >= 0


def _unique_fields(pairs: list[tuple[str, object]]) -> dict:
    values = {}
    for name, value in pairs:
        # Duplicate stop or room fields would give different readers conflicting intent.
        if name in values:
            raise ValueError("duplicate fields")
        values[name] = value
    return values
