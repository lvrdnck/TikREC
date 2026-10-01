"""Identity-checked quarantine boundary for one authorized removal."""

from __future__ import annotations

import os
from contextlib import nullcontext
from pathlib import Path

from .retention_authorization import (ArtifactFingerprint,
                                      check_fingerprint, fingerprint)


def require_identity_removal() -> None:
    """Require Windows handle exclusion or the approved managed Linux authority."""
    if os.name != "nt":
        from .managed_registry import current
        if current() is None:
            raise ValueError("destructive retention requires managed Linux service authority; "
                             "unmanaged POSIX retention is read-only")


def quarantine_relative(item: ArtifactFingerprint, operation_id: str,
                        index: int) -> str:
    """Name one private sibling from its durable operation and order position."""
    original = Path(item.relative_path)
    return str(original.with_name(f".tikrec-retention-{operation_id}-{index:06d}"))


def remove_authorized(root: Path, item: ArtifactFingerprint, volume,
                      digest: str | None, operation_id: str, index: int,
                      sync_parent, mutation_guard=nullcontext,
                      cleanup_errors: list[BaseException] | None = None) -> None:
    """Move, prove, then remove only the originally authorized filesystem object.

    A failed move or proof leaves the original or private sibling for manual
    inspection. The durable intent and attempt identify the private sibling.
    Later inner cleanup faults are exposed separately without replacing the first.
    """
    require_identity_removal()
    if os.name == "nt":
        from .retention_windows import HeldArtifact
    else:
        from .retention_linux import HeldArtifact

    original = root / item.relative_path
    private = root / quarantine_relative(item, operation_id, index)
    check_fingerprint(root, item, volume)
    if item.kind == "directory" and any(original.iterdir()):
        raise ValueError("retention parts directory is not empty")
    if os.path.lexists(private):
        raise ValueError("retention private quarantine name is occupied")

    first_error: BaseException | None = None
    later_errors: list[BaseException] = []

    # Python context exits can replace an active exception, so capture by identity.
    def remember(error: BaseException) -> None:
        nonlocal first_error
        if first_error is None:
            first_error = error
        elif error is not first_error and all(error is not later for later in later_errors):
            later_errors.append(error)

    held_artifact = HeldArtifact(original, item)
    try:
        with held_artifact as held:
            publish = (held.sync_parent if os.name != "nt" else lambda: sync_parent(private))
            try:
                # Both backends atomically refuse occupied destinations. Windows
                # holds an exclusive handle; Linux holds enforced service exclusion.
                held.rename(private)
                publish()
                moved = fingerprint(root, private, directory=item.kind == "directory",
                                    volume=volume)
                if not _same_moved_identity(item, moved):
                    raise ValueError("retention quarantined artifact identity changed")
                held.prove(digest)
                if os.path.lexists(original):
                    raise ValueError("retention original path reappeared after quarantine")
                # Windows shares policy authority only at final removal. Managed
                # Linux additionally excludes all promotions throughout proof.
                with mutation_guard():
                    try:
                        held.delete()
                        publish()
                        if os.path.lexists(private) or os.path.lexists(original):
                            raise ValueError("retention pathname reappeared after removal")
                    except BaseException as error:
                        # Capture the body fault before policy cleanup can replace it.
                        remember(error)
                        raise
            except BaseException as error:
                # Capture the operation or policy fault before the held handle exits.
                remember(error)
                raise
    except BaseException as error:
        remember(error)
        if held_artifact.enter_cleanup_error is not None:
            remember(held_artifact.enter_cleanup_error)
        if cleanup_errors is not None:
            cleanup_errors.extend(later_errors)
        if error is first_error:
            raise
        # Re-raise the original type for the failed event and public result.
        raise first_error from error


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
