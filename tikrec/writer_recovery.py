"""Recover only the writer partial proven to belong to one crashed service job."""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .flv import FlvFormatError, read_tag
from .finalize import _temporary_output_path
from .media import inspect_media
from .part_validation import validate_part
from .session_parts import RetainedParts, _check_structure, _discover_parts
from .writer import _FLV_HEADER
from .writer_recovery_evidence import (evidence_name, file_sha256, recovery_records,
                                       validate_recorded_evidence)


_PARTIAL = re.compile(r"\.part-([0-9]+)\.flv\.partial")
_EVIDENCE = re.compile(
    r"\.tikrec-writer-crash-([0-9a-f-]+)-part-([0-9]+)\.evidence"
)
_STAGING = re.compile(
    r"\.tikrec-writer-recovery-([0-9a-f-]+)-part-([0-9]+)\.tmp"
)
_RECOVERY_REASON = "writer_partial_recovery"


@dataclass(frozen=True)
class WriterPartialPlan:
    """One owned crash artifact and the immutable media derived from its prefix."""

    partial: Path
    evidence: Path
    staging: Path
    recovered: Path
    source_bytes: int
    source_sha256: str
    recovered_bytes: int
    retained: RetainedParts

    @property
    def truncated(self) -> bool:
        """Return whether an incomplete trailing tag is excluded from recovery."""
        return self.recovered_bytes != self.source_bytes


@dataclass(frozen=True)
class WriterStorage:
    """Validated completed media plus an optional pending writer recovery."""

    retained: RetainedParts
    recovery: WriterPartialPlan | None = None


def inspect_writer_storage(directory: Path, job, manifest: dict) -> WriterStorage:
    """Inspect writer artifacts without changing the original or derived bytes."""
    directory = Path(directory)
    entries = tuple(directory.iterdir()) if directory.is_dir() else ()
    partials = tuple(path for path in entries if ".partial" in path.name.lower())
    evidence = tuple(path for path in entries if path.name.startswith(".tikrec-writer-crash-"))
    staging = tuple(path for path in entries if path.name.startswith(".tikrec-writer-recovery-"))
    for path in partials:
        if _PARTIAL.fullmatch(path.name) is None:
            raise ValueError("non-writer partial artifact blocks recovery")
    for path in evidence + staging:
        pattern = _EVIDENCE if path in evidence else _STAGING
        match = pattern.fullmatch(path.name)
        if match is None or match.group(1) != job.session_id:
            raise ValueError("unowned writer recovery artifact blocks recovery")
        index = int(match.group(2))
        expected = (_evidence_path(directory, job.session_id, index) if path in evidence
                    else directory / f".tikrec-writer-recovery-{job.session_id}-part-{index:04d}.tmp")
        if path != expected:
            raise ValueError("noncanonical writer recovery artifact blocks recovery")

    completed = _discover_parts(
        directory,
        permitted_artifacts=partials + evidence + staging,
        require_media=False,
    )
    records = recovery_records(manifest)
    recorded_indexes = validate_recorded_evidence(directory, completed, records, evidence)
    unrecorded = [path for path in evidence if _evidence_index(path) not in recorded_indexes]
    if len(partials) > 1 or len(unrecorded) > 1 or len(staging) > 1:
        raise ValueError("multiple writer recovery artifacts are ambiguous")
    if partials and unrecorded:
        raise ValueError("writer partial and recovery evidence coexist")

    marker = job.state == "recovering" and job.recovery_reason == _RECOVERY_REASON
    if partials:
        if staging:
            raise ValueError("writer partial and recovery staging coexist")
        index = completed.next_index
        partial = partials[0]
        if (type(manifest.get("part_count")) is not int
                or manifest["part_count"] > len(completed.parts)):
            raise ValueError("manifest count cannot own the active writer partial")
        if partial.name != f".part-{index:04d}.flv.partial":
            raise ValueError("writer partial has an unexpected index")
        if not _active_ownership(job, manifest, marker):
            raise ValueError("writer partial lacks active recording ownership")
        return _plan(directory, job.session_id, completed, partial, index)

    if unrecorded:
        if not marker or not _active_ownership(job, manifest, marker):
            raise ValueError("writer evidence lacks committed recovery ownership")
        source = unrecorded[0]
        index = _evidence_index(source)
        expected_staging = directory / (
            f".tikrec-writer-recovery-{job.session_id}-part-{index:04d}.tmp"
        )
        if staging and staging[0] != expected_staging:
            raise ValueError("writer recovery staging has a conflicting index")
        final = directory / f"part-{index:04d}.flv"
        if final in completed.parts:
            if index != completed.next_index - 1:
                raise ValueError("recovered writer evidence conflicts with completed parts")
            prior = RetainedParts(completed.parts[:-1], index)
        else:
            if index != completed.next_index:
                raise ValueError("writer evidence has an unexpected index")
            prior = completed
        if (type(manifest.get("part_count")) is not int
                or manifest["part_count"] > len(prior.parts)):
            raise ValueError("manifest count conflicts with pending writer recovery")
        return _plan(directory, job.session_id, prior, source, index,
                     published=final in completed.parts)

    if staging:
        raise ValueError("writer recovery staging lacks preserved source evidence")
    if not completed.parts:
        raise ValueError("recovery requires completed or recoverable media")
    return WriterStorage(completed)


def recover_writer_partial(
    plan: WriterPartialPlan,
    *,
    validator: Callable[[Path], None] | None = None,
) -> Path:
    """Preserve the source, validate a separate copy, and atomically publish it."""
    validator = validator or _validate_media
    if plan.partial.exists() or plan.partial.is_symlink():
        _require_source(plan.partial, plan.source_bytes, plan.source_sha256)
        if plan.evidence.exists() or plan.evidence.is_symlink():
            raise ValueError("writer evidence destination already exists")
        os.replace(plan.partial, plan.evidence)
        _sync_directory(plan.evidence.parent)
    _require_source(plan.evidence, plan.source_bytes, plan.source_sha256)

    if plan.recovered.exists() or plan.recovered.is_symlink():
        if (plan.recovered.is_symlink() or not plan.recovered.is_file()
                or plan.recovered.stat().st_size != plan.recovered_bytes
                or not _same_prefix(plan.evidence, plan.recovered, plan.recovered_bytes)):
            raise ValueError("published recovered part conflicts with crash evidence")
        validator(plan.recovered)
        return plan.recovered

    if plan.staging.exists() or plan.staging.is_symlink():
        if plan.staging.is_symlink() or not plan.staging.is_file():
            raise ValueError("writer recovery staging is not a regular file")
        # This exact path is owned only after durable recovery intent and preserved evidence.
        plan.staging.unlink()
    _copy_prefix(plan.evidence, plan.staging, plan.recovered_bytes)
    try:
        validator(plan.staging)
        if plan.recovered.exists() or plan.recovered.is_symlink():
            raise ValueError("recovered part destination changed during validation")
        os.replace(plan.staging, plan.recovered)
        _sync_directory(plan.recovered.parent)
    except BaseException:
        plan.staging.unlink(missing_ok=True)
        raise
    return plan.recovered


def _plan(directory, session_id, prior, source, index, *, published=False):
    final = directory / f"part-{index:04d}.flv"
    if not published and (final.exists() or final.is_symlink()):
        raise ValueError("completed part conflicts with writer partial")
    evidence = _evidence_path(directory, session_id, index)
    partial = directory / f".part-{index:04d}.flv.partial"
    if source == partial and (evidence.exists() or evidence.is_symlink()):
        raise ValueError("writer evidence destination already exists")
    _require_regular_source(source)
    complete = _complete_prefix(source)
    _check_structure(source, byte_count=complete)
    retained = RetainedParts(prior.parts + (final,), index + 1)
    staging = directory / f".tikrec-writer-recovery-{session_id}-part-{index:04d}.tmp"
    return WriterStorage(retained, WriterPartialPlan(
        partial, evidence, staging, final, source.stat().st_size, file_sha256(source),
        complete, retained,
    ))


def _complete_prefix(path: Path) -> int:
    with path.open("rb") as handle:
        if handle.read(len(_FLV_HEADER)) != _FLV_HEADER:
            raise ValueError("writer partial has a non-writer FLV header")
        last_complete = handle.tell()
        while True:
            try:
                tag = read_tag(handle)
            except EOFError:
                return last_complete
            except FlvFormatError as error:
                raise ValueError("writer partial has malformed FLV framing") from error
            if tag is None:
                return last_complete
            last_complete = handle.tell()


def _active_ownership(job, manifest, marker):
    output = Path(job.output_path)
    temporary = _temporary_output_path(output)
    return (
        not job.stop_requested
        and job.room_id is not None
        and (job.state == "recording" or marker)
        and manifest.get("status") == "recording"
        and manifest.get("ended_at") is None
        and manifest.get("room_id") == job.room_id
        and manifest.get("finalization", {}).get("status") in {"pending", "not_started"}
        and not output.exists() and not output.is_symlink()
        and not temporary.exists() and not temporary.is_symlink()
    )


def _validate_media(path: Path) -> None:
    _check_structure(path)
    problems, _warnings = validate_part(path, "ffprobe", subprocess.run)
    info = inspect_media(path)
    if problems or info is None or info.video_codec is None:
        raise ValueError("recovered writer part failed media validation")


def _require_regular_source(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size == 0:
        raise ValueError("writer crash artifact is not a nonempty regular file")


def _require_source(path, size, digest):
    _require_regular_source(path)
    if path.stat().st_size != size or file_sha256(path) != digest:
        raise ValueError("writer crash artifact changed after inspection")


def _copy_prefix(source, destination, count):
    remaining = count
    with source.open("rb") as reader, destination.open("xb") as writer:
        while remaining:
            chunk = reader.read(min(64 * 1024, remaining))
            if not chunk:
                raise ValueError("writer crash artifact shortened during recovery")
            if writer.write(chunk) != len(chunk):
                raise OSError("short write while copying recovered writer prefix")
            remaining -= len(chunk)
        writer.flush()
        os.fsync(writer.fileno())


def _same_prefix(source, recovered, count):
    with source.open("rb") as left, recovered.open("rb") as right:
        remaining = count
        while remaining:
            size = min(64 * 1024, remaining)
            if left.read(size) != right.read(size):
                return False
            remaining -= size
    return True


def _evidence_path(directory, session_id, index):
    return directory / evidence_name(session_id, index)


def _evidence_index(path):
    match = _EVIDENCE.fullmatch(path.name)
    if match is None:
        raise ValueError("invalid writer evidence name")
    return int(match.group(2))


def _sync_directory(directory):
    if os.name != "nt":
        descriptor = os.open(directory, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
