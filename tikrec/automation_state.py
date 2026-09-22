"""Strict restart-safe state for unattended recording idempotence."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import UUID

from .creator_identity import validate_creator_handle
from .tiktok_identity import canonical_room_id


AUTOMATION_SCHEMA_VERSION = 1


class AutomationStateError(ValueError):
    """Automation state is corrupt or unsafe and must remain untouched."""


@dataclass(frozen=True)
class PendingAutomaticStart:
    """Durable claim spanning the controller-start crash window."""

    creator: str
    room_id: str
    output_path: str
    parts_directory: str
    previous_session_id: str | None = None

    def validate(self) -> None:
        """Reject unsafe identity or candidate path facts."""
        validate_creator_handle(self.creator)
        if canonical_room_id(self.room_id) != self.room_id:
            raise AutomationStateError("invalid automation state")
        output = _absolute_path(self.output_path)
        parts = _absolute_path(self.parts_directory)
        if output.suffix.lower() != ".mp4" or parts != output.with_name(
            f"{output.stem}.parts"
        ):
            raise AutomationStateError("invalid automation state")
        if self.previous_session_id is not None:
            try:
                canonical = str(UUID(self.previous_session_id))
            except (TypeError, ValueError):
                raise AutomationStateError("invalid automation state") from None
            if self.previous_session_id != canonical:
                raise AutomationStateError("invalid automation state")


@dataclass(frozen=True)
class AutomationState:
    """Consumed room identities plus at most one pending start claim."""

    consumed_rooms: tuple[tuple[str, str], ...] = ()
    pending_claim: PendingAutomaticStart | None = None
    schema_version: int = AUTOMATION_SCHEMA_VERSION

    def validate(self) -> None:
        """Validate the complete allowlisted state document."""
        if type(self.schema_version) is not int or self.schema_version != 1:
            raise AutomationStateError("invalid automation state")
        creators = []
        for creator, room_id in self.consumed_rooms:
            validate_creator_handle(creator)
            if canonical_room_id(room_id) != room_id:
                raise AutomationStateError("invalid automation state")
            creators.append(creator)
        if creators != sorted(creators) or len(creators) != len(set(creators)):
            raise AutomationStateError("invalid automation state")
        if self.pending_claim is not None:
            self.pending_claim.validate()

    def consumed(self) -> dict[str, str]:
        """Return a mutable copy for one atomic state transition."""
        return dict(self.consumed_rooms)


class AutomationStateStore:
    """Atomically load and replace the dedicated automation state document."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def load(self) -> AutomationState:
        """Return empty state when absent and reject ambiguous committed data."""
        try:
            with self.path.open("r", encoding="utf-8") as handle:
                document = json.load(handle, object_pairs_hook=_unique_fields)
        except FileNotFoundError:
            return AutomationState()
        except (OSError, UnicodeError, ValueError):
            raise AutomationStateError("automation state is unavailable") from None
        try:
            if not isinstance(document, dict) or set(document) != {
                "schema_version", "consumed_rooms", "pending_claim"
            }:
                raise AutomationStateError("invalid automation state")
            consumed = document["consumed_rooms"]
            if not isinstance(consumed, dict):
                raise AutomationStateError("invalid automation state")
            claim = _claim(document["pending_claim"])
            state = AutomationState(
                consumed_rooms=tuple(sorted(consumed.items())),
                pending_claim=claim,
                schema_version=document["schema_version"],
            )
            state.validate()
            return state
        except (TypeError, ValueError):
            raise AutomationStateError("invalid automation state") from None

    def save(self, state: AutomationState) -> None:
        """Flush a complete state document before atomic replacement."""
        state.validate()
        document = {
            "schema_version": state.schema_version,
            "consumed_rooms": state.consumed(),
            "pending_claim": _claim_document(state.pending_claim),
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary: Path | None = None
        try:
            with NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=self.path.parent,
                prefix=f".{self.path.name}.", suffix=".partial", delete=False,
            ) as handle:
                temporary = Path(handle.name)
                json.dump(document, handle, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
            if os.name != "nt":
                descriptor = os.open(self.path.parent, os.O_RDONLY)
                try:
                    os.fsync(descriptor)
                finally:
                    os.close(descriptor)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)


def _claim(value: object) -> PendingAutomaticStart | None:
    if value is None:
        return None
    fields = {
        "creator", "room_id", "output_path", "parts_directory",
        "previous_session_id",
    }
    if not isinstance(value, dict) or set(value) != fields:
        raise AutomationStateError("invalid automation state")
    return PendingAutomaticStart(**value)


def _claim_document(claim: PendingAutomaticStart | None) -> dict | None:
    if claim is None:
        return None
    return {
        "creator": claim.creator,
        "room_id": claim.room_id,
        "output_path": claim.output_path,
        "parts_directory": claim.parts_directory,
        "previous_session_id": claim.previous_session_id,
    }


def _absolute_path(value: object) -> Path:
    if (not isinstance(value, str) or not value or "\x00" in value
            or "://" in value or not Path(value).is_absolute()):
        raise AutomationStateError("invalid automation state")
    return Path(value)


def _unique_fields(pairs: list[tuple[str, object]]) -> dict[str, object]:
    values = {}
    for name, value in pairs:
        if name in values:
            raise ValueError("duplicate automation state field")
        values[name] = value
    return values
