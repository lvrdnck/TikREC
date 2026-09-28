"""Identity-checked quarantine boundary for one authorized removal."""

from __future__ import annotations

import os
from pathlib import Path

from .retention_authorization import (ArtifactFingerprint, _checked_digest,
                                      check_fingerprint, fingerprint)


def quarantine_relative(item: ArtifactFingerprint, operation_id: str,
                        index: int) -> str:
    """Name one private sibling from its durable operation and order position."""
    original = Path(item.relative_path)
    return str(original.with_name(f".tikrec-retention-{operation_id}-{index:06d}"))


def remove_authorized(root: Path, item: ArtifactFingerprint, volume,
                      digest: str | None, operation_id: str, index: int,
                      sync_parent) -> None:
    """Move, prove, then remove only the originally authorized filesystem object.

    A failed move or proof leaves the original or private sibling for manual
    inspection. The durable intent and attempt identify the private sibling.
    """
    original = root / item.relative_path
    private = root / quarantine_relative(item, operation_id, index)
    check_fingerprint(root, item, volume)
    if item.kind == "directory" and any(original.iterdir()):
        raise ValueError("retention parts directory is not empty")
    if os.path.lexists(private):
        raise ValueError("retention private quarantine name is occupied")
    # Same-directory rename isolates a stable name before any irreversible remove.
    original.rename(private)
    sync_parent(private)
    moved = fingerprint(root, private, directory=item.kind == "directory", volume=volume)
    if not _same_moved_identity(item, moved):
        raise ValueError("retention quarantined artifact identity changed")
    if item.kind == "directory":
        if any(private.iterdir()):
            raise ValueError("retention quarantined parts directory is not empty")
    elif digest is None or _checked_digest(root, moved, volume) != digest:
        raise ValueError("retention quarantined artifact byte proof changed")
    if os.path.lexists(original):
        raise ValueError("retention original path reappeared after quarantine")
    if item.kind == "directory":
        private.rmdir()
    else:
        private.unlink()
    sync_parent(private)


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
    # POSIX rename changes ctime; a file's content and other identity must hold.
    return ((before.mode, before.size, before.device, before.inode,
             before.mtime_ns, before.link_count, before.attributes)
            == (after.mode, after.size, after.device, after.inode,
                after.mtime_ns, after.link_count, after.attributes))
