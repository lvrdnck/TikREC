"""Immutable one-session deletion authority derived from fresh retention evidence."""

from __future__ import annotations

import json
import math
import os
import re
import stat
from dataclasses import asdict, dataclass
from pathlib import Path

from .configuration import Configuration, ConfigurationStore
from .job_state import JobStateStore
from .retention_locality import LocalVolume, local_volume, proven_local
from .retention_paths import local_path
from .retention_snapshot import ClaimSnapshot, capture_claim, capture_root
from .service_job import default_job_state_path, second_job_state_path
from .writer_recovery_evidence import recovery_records


@dataclass(frozen=True)
class ArtifactFingerprint:
    """No-follow identity for one exact authorized path."""

    relative_path: str
    kind: str
    mode: int
    size: int
    device: int
    inode: int
    mtime_ns: int
    ctime_ns: int
    link_count: int
    attributes: int
    volume: LocalVolume

    def audit_dict(self) -> dict:
        """Render non-secret artifact identity in the durable intent."""
        return asdict(self)


@dataclass(frozen=True)
class DeletionAuthorization:
    """One immutable bounded allowlist and all non-target claims."""

    root: Path
    root_identity: tuple
    volume: LocalVolume
    session_id: str
    creator: str
    ended_at: float
    max_age_days: int
    protected_creators: tuple[str, ...]
    parts: ArtifactFingerprint
    output: ArtifactFingerprint
    order: tuple[ArtifactFingerprint, ...]
    other_claims: tuple[ClaimSnapshot, ...]


def authorize(root: Path, session: dict, config: Configuration) -> DeletionAuthorization:
    """Bind current eligible planner result to exact local artifact identities."""
    root = local_path(root, directory=True)
    if session["classification"] != "eligible" or session["protected"]:
        raise ValueError("retention session is not eligible")
    directory, output = Path(session["parts_directory"]), Path(session["output_path"])
    if (directory.parent != root or output.parent != root
            or output != directory.with_suffix(".mp4")):
        raise ValueError("retention session paths are outside the selected root")
    volume = local_volume(root)
    if volume is None or not proven_local(root):
        raise ValueError("retention root locality changed")
    snapshot = capture_root(root, capture_claim)
    if not snapshot.stable or any(claim.uncertain for claim in snapshot.claims):
        raise ValueError("retention claimant evidence is unstable")
    matches = [claim for claim in snapshot.claims if claim.session_id == session["session_id"]]
    if (len(matches) != 1 or matches[0].directory != str(directory)
            or matches[0].output_path != str(output)):
        raise ValueError("retention claimant changed")
    manifest = json.loads((directory / "session.json").read_text(encoding="utf-8"))
    if (manifest["session_id"] != session["session_id"]
            or manifest["creator"] != session["creator"]
            or manifest["ended_at"] != session["ended_at"]):
        raise ValueError("retention manifest changed")
    media = {record["evidence"] for record in recovery_records(manifest)}
    children = list(directory.iterdir())
    for child in children:
        if re.fullmatch(r"part-[0-9]+\.flv", child.name):
            media.add(child.name)
    controls = {"session.json", "connections.jsonl"}
    if {child.name for child in children} != media | controls.intersection(
            {child.name for child in children}):
        raise ValueError("retention artifact allowlist is incomplete")
    if "session.json" not in {child.name for child in children}:
        raise ValueError("retention manifest disappeared")
    order_names = sorted(media)
    if "connections.jsonl" in {child.name for child in children}:
        order_names.append("connections.jsonl")
    order_names.extend(("session.json", directory.name, output.name))
    order = tuple(fingerprint(root, directory / name if name not in
                              {directory.name, output.name} else root / name,
                              directory=name == directory.name, volume=volume)
                  for name in order_names)
    return DeletionAuthorization(
        root, _directory_identity(root), volume, session["session_id"], session["creator"],
        session["ended_at"], config.retention_max_age_days,
        config.retention_protected_creators, order[-2], order[-1], order,
        tuple(claim for claim in snapshot.claims if claim.directory != str(directory)))


def fingerprint(root: Path, path: Path, *, directory: bool,
                volume: LocalVolume) -> ArtifactFingerprint:
    """Require a local unredirected singly linked artifact and record its lstat."""
    path = local_path(path, directory=directory)
    details = path.lstat()
    if (not proven_local(path) or local_volume(path) != volume
            or not directory and details.st_nlink != 1
            or getattr(details, "st_file_attributes", 0) & 0x400):
        raise ValueError("retention artifact identity or locality is unsafe")
    return ArtifactFingerprint(str(path.relative_to(root)), "directory" if directory else "file",
                               details.st_mode, details.st_size, details.st_dev, details.st_ino,
                               details.st_mtime_ns, details.st_ctime_ns, details.st_nlink,
                               getattr(details, "st_file_attributes", 0), volume)


def check_fingerprint(root: Path, expected: ArtifactFingerprint,
                      volume: LocalVolume) -> None:
    """Recheck one artifact immediately before an authorized operation."""
    path = root / expected.relative_path
    current = fingerprint(root, path, directory=expected.kind == "directory", volume=volume)
    # Directory size/timestamps/link count change after removing its own children.
    if expected.kind == "directory":
        if ((current.mode, current.device, current.inode, current.link_count,
             current.attributes)
                != (expected.mode, expected.device, expected.inode,
                    expected.link_count, expected.attributes)):
            raise ValueError("retention parts directory identity changed")
    elif current != expected:
        raise ValueError("retention artifact identity changed")


def check_jobs(auth: DeletionAuthorization,
               job_paths: tuple[Path, Path] | None = None) -> None:
    """Refuse any current service slot referencing the target, even if completed."""
    if job_paths is not None and len(job_paths) != 2:
        raise ValueError("retention requires both durable service job slots")
    paths = job_paths or (default_job_state_path(), second_job_state_path())
    for path in paths:
        job = JobStateStore(path).load()
        if job is None:
            continue
        if (job.session_id == auth.session_id
                or _same_artifact(job.output_path, auth.root / auth.output.relative_path)
                or _same_artifact(job.parts_directory, auth.root / auth.parts.relative_path)):
            raise ValueError("durable service job still references retention target")


def check_policy(auth: DeletionAuthorization, store: ConfigurationStore, now: float) -> None:
    """Require the current rule to continue authorizing this ended session."""
    if type(now) not in {int, float} or not math.isfinite(now):
        raise ValueError("retention clock is invalid")
    current = store.load()
    current.validate()
    if (current.retention_max_age_days != auth.max_age_days
            or current.retention_protected_creators != auth.protected_creators
            or auth.max_age_days is None or auth.creator in current.retention_protected_creators
            or auth.ended_at > now - auth.max_age_days * 86400):
        raise ValueError("retention policy no longer authorizes target")


def check_root(auth: DeletionAuthorization, deleted: frozenset[str]) -> None:
    """Reject a changed root, new claimant, extra child, or remaining identity loss."""
    if (_directory_identity(local_path(auth.root, directory=True)) != auth.root_identity
            or not proven_local(auth.root) or local_volume(auth.root) != auth.volume):
        raise ValueError("retention root identity or locality changed")
    snapshot = capture_root(auth.root, capture_claim)
    # The target claim becomes incomplete as soon as its first artifact is removed.
    if not snapshot.stable:
        raise ValueError("retention root claimant observation is unstable")
    others = tuple(claim for claim in snapshot.claims
                   if claim.directory != str(auth.root / auth.parts.relative_path))
    if others != auth.other_claims:
        raise ValueError("retention non-target claim changed")
    for item in auth.order:
        path = auth.root / item.relative_path
        if item.relative_path in deleted:
            if path.exists() or path.is_symlink():
                raise ValueError("deleted retention artifact reappeared")
        else:
            check_fingerprint(auth.root, item, auth.volume)
    parts_path = auth.root / auth.parts.relative_path
    if auth.parts.relative_path not in deleted:
        expected = {Path(item.relative_path).name for item in auth.order
                    if item.relative_path not in deleted and item != auth.parts
                    and Path(item.relative_path).parent == Path(auth.parts.relative_path)}
        if {path.name for path in parts_path.iterdir()} != expected:
            raise ValueError("unexpected retention target artifact appeared")


def _directory_identity(path: Path) -> tuple:
    details = path.lstat()
    if not stat.S_ISDIR(details.st_mode):
        raise ValueError("retention root is not a directory")
    return (details.st_mode, details.st_dev, details.st_ino,
            getattr(details, "st_file_attributes", 0))


def _path_key(path: str | Path) -> str:
    return os.path.normcase(os.path.abspath(path))


def _same_artifact(first: str | Path, second: Path) -> bool:
    if _path_key(first) == _path_key(second):
        return True
    try:
        return os.path.samefile(first, second)
    except FileNotFoundError:
        return False
