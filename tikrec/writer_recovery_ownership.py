"""Read-only fresh ownership proof surrounding startup writer repair."""

from __future__ import annotations

import hashlib
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path

from .recovery_session import inspect_recovery_session
from .writer_recovery_evidence import file_sha256, same_prefix


@dataclass(frozen=True)
class WriterRecoveryOwnership:
    """Immutable authorization for one job, manifest, and writer partial."""

    manifest_digest: str
    values: dict
    plan: object


def capture_writer_ownership(session) -> WriterRecoveryOwnership:
    """Bind the initial inspection to the exact manifest bytes currently on disk."""
    if session.writer_recovery is None:
        raise ValueError("writer recovery has no owned partial")
    content = session.manifest.path.read_bytes()
    return WriterRecoveryOwnership(hashlib.sha256(content).hexdigest(),
                                   deepcopy(session.manifest.snapshot()),
                                   session.writer_recovery)


def verify_writer_ownership(token: WriterRecoveryOwnership, job, store, *,
                            clock, media_inspector) -> None:
    """Reinspect the current job and writer-compatible storage before mutation."""
    if (store.load() != job or _manifest_digest(token) != token.manifest_digest
            or token.values.get("room_id") != job.room_id
            or Path(token.values["output_path"]) != Path(job.output_path)
            or Path(token.values["parts_directory"]) != Path(job.parts_directory)):
        raise ValueError("writer recovery ownership changed")
    fresh = inspect_recovery_session(job, clock=clock, media_inspector=media_inspector)
    if (fresh.manifest.snapshot() != token.values
            or fresh.writer_recovery != token.plan
            or _manifest_digest(token) != token.manifest_digest
            or store.load() != job):
        raise ValueError("writer recovery ownership changed")


def verify_writer_commit(token: WriterRecoveryOwnership, job, store) -> None:
    """Revalidate manifest ownership and the authorized recovered source before append."""
    plan = token.plan
    if store.load() != job or _manifest_digest(token) != token.manifest_digest:
        raise ValueError("writer recovery ownership changed before manifest commit")
    if (not plan.evidence.is_file() or plan.evidence.is_symlink()
            or not plan.recovered.is_file() or plan.recovered.is_symlink()
            or plan.evidence.stat().st_size != plan.source_bytes
            or file_sha256(plan.evidence) != plan.source_sha256
            or plan.recovered.stat().st_size != plan.recovered_bytes
            or not same_prefix(plan.evidence, plan.recovered, plan.recovered_bytes)):
        raise ValueError("recovered writer media differs from authorized partial")
    if store.load() != job or _manifest_digest(token) != token.manifest_digest:
        raise ValueError("writer recovery ownership changed before manifest commit")


def verify_writer_phase(token: WriterRecoveryOwnership, job, store, source: Path) -> None:
    """Check current intent, manifest, and preserved bytes at a mutation boundary."""
    if store.load() != job or _manifest_digest(token) != token.manifest_digest:
        raise ValueError("writer recovery ownership changed")
    plan = token.plan
    if (source.is_symlink() or not source.is_file()
            or source.stat().st_size != plan.source_bytes
            or file_sha256(source) != plan.source_sha256):
        raise ValueError("writer crash source changed")
    if store.load() != job or _manifest_digest(token) != token.manifest_digest:
        raise ValueError("writer recovery ownership changed")


def _manifest_digest(token: WriterRecoveryOwnership) -> str:
    return hashlib.sha256((token.plan.partial.parent / "session.json").read_bytes()).hexdigest()
