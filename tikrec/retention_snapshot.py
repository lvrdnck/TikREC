"""Bounded immutable claims and whole-root evidence identity for retention."""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from dataclasses import dataclass
from pathlib import Path

from .retention_paths import local_path
from .session_resume import _unique_values


_CONTROL_LIMIT = 4 * 1024 * 1024


@dataclass(frozen=True)
class ClaimSnapshot:
    """One immediate claimant, including explicit absence and uncertainty."""

    directory: str
    evidence: tuple | None
    manifest_digest: str | None
    session_id: str | None
    output_state: str
    output_path: str | None
    output_key: str | None
    physical_output: tuple[int, int] | None
    output_stamp: tuple | None
    source_type: str | None
    creator: str | None
    uncertain: bool


@dataclass(frozen=True)
class RootSnapshot:
    """One bounded observation of root membership and all immediate claimants."""

    root_stamp: tuple
    claims: tuple[ClaimSnapshot, ...]


def capture_root(root: Path, claim_reader) -> RootSnapshot:
    """Observe the root and each immediate parts child in deterministic order."""
    local_path(root, directory=True)
    children = sorted((path for path in root.iterdir()
                       if path.name.lower().endswith(".parts")),
                      key=lambda path: (path.name.casefold(), path.name))
    return RootSnapshot(_stamp(root), tuple(claim_reader(path, root) for path in children))


def capture_claim(directory: Path, root: Path) -> ClaimSnapshot:
    """Collect supported claims independently of eventual eligibility."""
    evidence = digest = identity = output_path = key = physical = output_stamp = None
    source = creator = None
    state = "unknown"
    try:
        local_path(directory, directory=True)
        evidence = _evidence(directory)
        manifest = directory / "session.json"
        content = _control(manifest)
        digest = hashlib.sha256(content).hexdigest()
        values = json.loads(content.decode("utf-8"), object_pairs_hook=_unique_values)
        identity = values["session_id"]
        if type(identity) is not str or str(uuid.UUID(identity)) != identity:
            raise ValueError("invalid claimant UUID")
        source, creator = values.get("source_type"), values.get("creator")
        if "output_path" not in values:
            raise ValueError("missing output declaration")
        declared = values["output_path"]
        if declared is None:
            state = "null"
        else:
            if type(declared) is not str or not Path(declared).is_absolute():
                raise ValueError("invalid output declaration")
            output = Path(os.path.abspath(declared))
            if (output.parent != root or output.suffix.lower() != ".mp4"
                    or Path(declared) != output):
                raise ValueError("unsafe output claim")
            output_path, key, state = str(output), str(output).casefold(), "declared"
            try:
                details = output.lstat()
            except FileNotFoundError:
                pass  # An accepted pending output still has a lexical claim.
            else:
                local_path(output, directory=False)
                output_stamp = _stamp(output)
                physical = (details.st_dev, details.st_ino)
                if not details.st_ino or details.st_nlink > 1:
                    raise ValueError("output physical ownership is ambiguous")
        return ClaimSnapshot(str(directory), evidence, digest, identity, state,
                             output_path, key, physical, output_stamp, source, creator, False)
    except (OSError, UnicodeError, ValueError, TypeError, KeyError, AttributeError,
            OverflowError):
        return ClaimSnapshot(str(directory), evidence, digest, identity, "unknown",
                             output_path, key, physical, output_stamp, source, creator, True)


def _evidence(directory: Path) -> tuple:
    entries = [(_stamp(directory), None)]
    for path in sorted(directory.iterdir(), key=lambda item: item.name):
        content = _control(path) if path.name in {"session.json", "connections.jsonl"} else None
        entries.append((path.name, _stamp(path),
                        None if content is None else hashlib.sha256(content).hexdigest()))
    return tuple(entries)


def _control(path: Path) -> bytes:
    local_path(path, directory=False)
    with path.open("rb") as handle:
        content = handle.read(_CONTROL_LIMIT + 1)
    if len(content) > _CONTROL_LIMIT:
        raise ValueError("retention control evidence exceeds bounded inspection")
    return content


def _stamp(path: Path) -> tuple:
    details = path.lstat()
    return (details.st_mode, details.st_size, details.st_mtime_ns, details.st_ctime_ns,
            details.st_dev, details.st_ino, details.st_nlink,
            getattr(details, "st_file_attributes", 0))
