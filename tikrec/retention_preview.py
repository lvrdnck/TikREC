"""Read-only exact-target preview that can only veto fresh retention authority."""

from __future__ import annotations

import time
import hashlib
from contextlib import nullcontext
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .configuration import ConfigurationStore
from .media import MediaInfo, inspect_media
from .retention_execute import _fresh_authorization, _preview_signature
from .retention_mutation import require_identity_removal
from .retention_paths import local_path


@dataclass(frozen=True)
class RetentionPreview:
    """Owner-visible target facts plus an in-memory restrictive evidence guard."""

    root: Path
    session_id: str
    creator: str
    ended_at: float
    output: Path
    parts: Path
    file_count: int
    total_file_bytes: int
    guard: tuple


def prepare_preview(root: Path, session_id: str,
                    configuration_store: ConfigurationStore, *,
                    job_paths: tuple[Path, Path] | None = None,
                    clock: Callable[[], float] = time.time,
                    media_inspector: Callable[[Path], MediaInfo | None] = inspect_media
                    ) -> RetentionPreview:
    """Prove display facts without acquiring a lease or creating audit intent."""
    from .managed_registry import current
    authority = current()
    reservation = authority.retention_scope(root) if authority is not None else nullcontext()
    with reservation:
        if authority is not None:
            authority.check_retention_inputs(configuration_store.path, job_paths, None)
        return _prepare_preview(root, session_id, configuration_store,
                                job_paths=job_paths, clock=clock, media_inspector=media_inspector)


def _prepare_preview(root, session_id, configuration_store, *, job_paths, clock, media_inspector):
    """Observe an exact preview under managed exclusion when required."""
    require_identity_removal()
    scope = local_path(Path(root), directory=True)
    auth, evidence, config = _fresh_authorization(
        scope, session_id, configuration_store, job_paths, clock, media_inspector)
    files = [item for item in auth.order if item.kind == "file"]
    if len(files) != len(auth.order) - 1 or any(item.size < 0 for item in files):
        raise ValueError("retention preview artifact inventory is incomplete")
    return RetentionPreview(
        root=scope, session_id=auth.session_id, creator=auth.creator,
        ended_at=auth.ended_at, output=scope / auth.output.relative_path,
        parts=scope / auth.parts.relative_path, file_count=len(files),
        total_file_bytes=sum(item.size for item in files),
        guard=_preview_signature(auth, evidence, config))


def preview_digest(preview: RetentionPreview) -> str:
    """Bind the remote preview to a restrictive veto, never saved delete authority."""
    return hashlib.sha256(repr(preview.guard).encode("utf-8")).hexdigest()
