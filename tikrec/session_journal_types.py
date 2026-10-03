"""Validated orchestration inputs; callers must independently prove native evidence."""

from __future__ import annotations

import hashlib
import json
import math
import re
import uuid
from dataclasses import asdict, dataclass
from pathlib import PureWindowsPath

from .tiktok_identity import canonical_room_id


class JournalError(ValueError):
    """Journal authority or an input is invalid; preserve existing state."""


class JournalBusy(JournalError):
    """A bounded lock wait expired; authority was not proved corrupt."""


class JournalConflict(JournalError):
    """Ownership, capacity or a guarded predecessor prevents this operation."""


class JournalUncertain(JournalError):
    """Commit outcome requires durable operation lookup before any retry/refund."""


def require(condition: bool, message: str = "invalid journal input") -> None:
    """Reject an invalid input without echoing untrusted evidence values."""
    if not condition:
        raise JournalError(message)


def identifier(value: str) -> None:
    """Require a canonical UUID operation, catalog, session or attempt identity."""
    try:
        require(type(value) is str and str(uuid.UUID(value)) == value)
    except (ValueError, TypeError, AttributeError) as error:
        raise JournalError("invalid journal identity") from error


def timestamp(value: float) -> None:
    """Require a finite nonnegative wall-clock observation."""
    require(type(value) in {float, int} and math.isfinite(value) and value >= 0)


def room(value: str | None) -> None:
    """Validate canonical public room identity, retaining unknown as unknown."""
    if value is not None:
        try:
            require(type(value) is str and len(value) <= 128
                    and canonical_room_id(value) == value)
        except ValueError as error:
            raise JournalError("invalid journal room") from error


def encode(value: object) -> str:
    """Encode bounded validated records deterministically for receipts and seals."""
    result = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    require(len(result.encode("utf-8")) <= 1024 * 1024, "journal evidence too large")
    return result


def intent_from_record(record: str) -> SessionIntent:
    """Revalidate immutable intent without reading media or a native filesystem."""
    values = json.loads(record)
    for key in ("root", "output", "parts"):
        identity = values[key]
        values[key] = ArtifactIdentity(identity["volume"], tuple(identity["components"]))
    return SessionIntent(**values)


def digest(value: object) -> str:
    """Hash canonical evidence or operation arguments without inspecting media."""
    return hashlib.sha256(encode(value).encode("utf-8")).hexdigest()


def sha256(value: str) -> None:
    """Require a lowercase SHA256 evidence digest."""
    require(type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None)


def closure_from_record(value: str) -> ClosureSeal:
    """Revalidate persisted closure records; no filesystem or media proof is inferred."""
    record = json.loads(value)
    artifacts = []
    for item in record.pop("artifacts"):
        native = item.pop("identity")
        artifacts.append(ClosedArtifact(ArtifactIdentity(native["volume"], tuple(native["components"])),
                                        **item))
    record["artifacts"] = tuple(artifacts)
    record["warnings"] = tuple(record["warnings"])
    return ClosureSeal(**record)


@dataclass(frozen=True)
class ArtifactIdentity:
    """Caller-proven native volume and canonical component key, including aliases.

    This key is NOT derived from a displayed path by the journal. A future native
    adapter must prove parent/volume/alias identity before constructing it.
    """

    volume: str
    components: tuple[str, ...]

    def __post_init__(self) -> None:
        require(type(self.volume) is str and 0 < len(self.volume) <= 128
                and self.volume == self.volume.casefold() and "\x00" not in self.volume)
        require(type(self.components) is tuple and 0 < len(self.components) <= 128)
        for component in self.components:
            require(type(component) is str and 0 < len(component) <= 255
                    and component == component.casefold() and component not in {".", ".."}
                    and not any(c in component for c in "\\/:\x00"))

    def overlaps(self, other: ArtifactIdentity) -> bool:
        """Protect both equality and subtree overlaps on a proven native volume."""
        count = min(len(self.components), len(other.components))
        return (self.volume == other.volume
                and self.components[:count] == other.components[:count])

    def contains(self, other: ArtifactIdentity) -> bool:
        """Check that an inventory entry belongs to its claimed native subtree."""
        return (self.volume == other.volume
                and other.components[:len(self.components)] == self.components)


@dataclass(frozen=True)
class SessionIntent:
    """Immutable accepted session identity/raw policy and caller-proven path keys."""

    session_id: str
    creator: str
    expected_room: str | None
    output_path: str
    parts_path: str
    root: ArtifactIdentity
    output: ArtifactIdentity
    parts: ArtifactIdentity
    raw_copy: bool
    started_at: float
    automatic_claim: str | None = None

    def __post_init__(self) -> None:
        identifier(self.session_id)
        require(type(self.creator) is str and self.creator == self.creator.casefold()
                and re.fullmatch(r"[a-z0-9_.]{1,64}", self.creator) is not None)
        room(self.expected_room)
        timestamp(self.started_at)
        require(type(self.raw_copy) is bool)
        require(all(type(x) is ArtifactIdentity for x in (self.root, self.output, self.parts)))
        require(self.root.contains(self.output) and self.root.contains(self.parts)
                and not self.output.overlaps(self.parts))
        require(type(self.output_path) is str and type(self.parts_path) is str
                and len(self.output_path) <= 4096 and len(self.parts_path) <= 4096)
        output, parts = PureWindowsPath(self.output_path), PureWindowsPath(self.parts_path)
        require(output.is_absolute() and parts.is_absolute()
                and output.suffix.casefold() == ".mp4"
                and parts == output.with_suffix(".parts"))
        if self.automatic_claim is not None:
            identifier(self.automatic_claim)
            require(self.expected_room is not None)


@dataclass(frozen=True)
class ClosedArtifact:
    """Stored native closure observation; not a writer-handle or decoder proof."""

    identity: ArtifactIdentity
    role: str
    size: int
    stamp: str
    control_hash: str | None = None

    def __post_init__(self) -> None:
        require(type(self.identity) is ArtifactIdentity)
        require(type(self.role) is str and self.role in {"flv", "raw", "arrivals", "manifest", "connections"})
        name = self.identity.components[-1]
        patterns = {"flv": r"part-[0-9]{4,}\.flv", "raw": r"connection-[0-9]{4,}\.raw",
                    "arrivals": r"connection-[0-9]{4,}\.arrivals\.jsonl",
                    "manifest": r"session\.json", "connections": r"connections\.jsonl"}
        require(re.fullmatch(patterns[self.role], name) is not None, "invalid evidence filename")
        require(type(self.size) is int and self.size >= 0)
        require(type(self.stamp) is str and 0 < len(self.stamp) <= 128)
        if self.role in {"manifest", "connections"}:
            sha256(self.control_hash)
        else:
            require(self.control_hash is None)


@dataclass(frozen=True)
class ClosureSeal:
    """Validated immutable closure inventory supplied after independent proof."""

    session_id: str
    generation: int
    room_id: str
    raw_copy: bool
    ended_at: float
    artifacts: tuple[ClosedArtifact, ...]
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        identifier(self.session_id)
        require(type(self.generation) is int and self.generation > 0)
        room(self.room_id)
        require(self.room_id is not None and type(self.raw_copy) is bool)
        timestamp(self.ended_at)
        require(type(self.artifacts) is tuple and 3 <= len(self.artifacts) <= 4096)
        require(all(type(x) is ClosedArtifact for x in self.artifacts))
        identities = [encode(asdict(x.identity)) for x in self.artifacts]
        require(len(identities) == len(set(identities)))
        roles = [x.role for x in self.artifacts]
        require(roles.count("manifest") == 1 and roles.count("connections") == 1
                and "flv" in roles)
        require(self.raw_copy or not ({"raw", "arrivals"} & set(roles)))
        require(type(self.warnings) is tuple and len(self.warnings) <= 64)
        require(all(type(x) is str and re.fullmatch(r"[a-z_]{1,64}", x)
                    for x in self.warnings))


@dataclass(frozen=True)
class SettlementProof:
    """Caller-proven attempt exit/publication binding; journal does no media I/O."""

    session_id: str
    attempt_token: str
    seal_hash: str
    exit_identity: str
    output: ArtifactIdentity
    output_size: int
    output_hash: str
    manifest_hash: str

    def __post_init__(self) -> None:
        identifier(self.session_id)
        identifier(self.attempt_token)
        sha256(self.seal_hash)
        sha256(self.output_hash)
        sha256(self.manifest_hash)
        require(type(self.exit_identity) is str and 0 < len(self.exit_identity) <= 128)
        require(type(self.output) is ArtifactIdentity and type(self.output_size) is int
                and self.output_size > 0)


@dataclass(frozen=True)
class AttemptExitProof:
    """Caller-proven process exit tied to an attempt; not inferred from a heartbeat."""

    session_id: str
    attempt_token: str
    exit_identity: str

    def __post_init__(self) -> None:
        identifier(self.session_id)
        identifier(self.attempt_token)
        require(type(self.exit_identity) is str and 0 < len(self.exit_identity) <= 128)


@dataclass(frozen=True)
class ReservationReleaseProof:
    """Caller-proven no-writer disposition, bound to one unadmitted reservation."""

    session_id: str
    generation: int
    authority_identity: str

    def __post_init__(self) -> None:
        identifier(self.session_id)
        require(type(self.generation) is int and self.generation > 0)
        require(type(self.authority_identity) is str and 0 < len(self.authority_identity) <= 128)
