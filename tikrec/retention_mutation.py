"""Identity-checked quarantine boundary for one authorized removal."""

from __future__ import annotations

import os
from contextlib import nullcontext
from pathlib import Path

from .retention_authorization import (ArtifactFingerprint,
                                      check_fingerprint, fingerprint)


def require_identity_removal() -> None:
    """Refuse platforms without the approved exact-object removal primitive."""
    if os.name != "nt":
        raise ValueError("destructive retention requires Windows handle-based removal; "
                         "POSIX retention is read-only")


def quarantine_relative(item: ArtifactFingerprint, operation_id: str,
                        index: int) -> str:
    """Name one private sibling from its durable operation and order position."""
    original = Path(item.relative_path)
    return str(original.with_name(f".tikrec-retention-{operation_id}-{index:06d}"))


def remove_authorized(root: Path, item: ArtifactFingerprint, volume,
                      digest: str | None, operation_id: str, index: int,
                      sync_parent, mutation_guard=nullcontext) -> None:
    """Move, prove, then remove only the originally authorized filesystem object.

    A failed move or proof leaves the original or private sibling for manual
    inspection. The durable intent and attempt identify the private sibling.
    """
    require_identity_removal()
    from .retention_windows import HeldArtifact

    original = root / item.relative_path
    private = root / quarantine_relative(item, operation_id, index)
    check_fingerprint(root, item, volume)
    if item.kind == "directory" and any(original.iterdir()):
        raise ValueError("retention parts directory is not empty")
    if os.path.lexists(private):
        raise ValueError("retention private quarantine name is occupied")
    with HeldArtifact(original, item) as held:
        # The kernel refuses an occupied destination atomically, including a
        # collision after lexists. The same exclusive handle owns the whole step.
        held.rename(private)
        sync_parent(private)
        moved = fingerprint(root, private, directory=item.kind == "directory", volume=volume)
        if not _same_moved_identity(item, moved):
            raise ValueError("retention quarantined artifact identity changed")
        held.prove(digest)
        if os.path.lexists(original):
            raise ValueError("retention original path reappeared after quarantine")
        # Hashing and reversible quarantine do not delay config promotion. Only
        # the final policy/job recheck and exact-handle removal share authority.
        with mutation_guard():
            held.delete()
            sync_parent(private)
            if os.path.lexists(private) or os.path.lexists(original):
                raise ValueError("retention pathname reappeared after removal")


def _same_moved_identity(before: ArtifactFingerprint,
                         after: ArtifactFingerprint) -> bool:
    """Ignore only metadata a same-directory rename or child removal changes."""
    if before.kind != after.kind or before.volume != after.volume:
        return False
    if before.kind == "directory":
        return ((before.mode, before.device, before.inode, before.link_count,
                 before.attributes)
                == (after.mode, after.device, after.inode, after.link_count,
                    after.attributes))
    # Rename/cross-API ctime is not invariant; held file bytes and identity are.
    return ((before.mode, before.size, before.device, before.inode,
             before.mtime_ns, before.link_count, before.attributes)
            == (after.mode, after.size, after.device, after.inode,
                after.mtime_ns, after.link_count, after.attributes))
