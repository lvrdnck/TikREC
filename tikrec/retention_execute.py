"""Internal one-session destructive retention with fresh bounded authorization."""

from __future__ import annotations

import time
import uuid
import os
from collections.abc import Callable
from pathlib import Path

from .configuration import ConfigurationStore
from .lifecycle_lock import acquire_lifecycle
from .media import MediaInfo, inspect_media
from .retention_audit import RetentionAudit
from .retention_authorization import (authorize, check_fingerprint, check_jobs,
                                      check_policy, check_root)
from .retention_paths import local_path
from .retention_plan import plan_retention


def execute_retention(root: Path, session_id: str, configuration_store: ConfigurationStore,
                      *, audit_path: Path | None = None,
                      job_paths: tuple[Path, Path] | None = None,
                      clock: Callable[[], float] = time.time,
                      media_inspector: Callable[[Path], MediaInfo | None] = inspect_media,
                      before_mutation: Callable[[Path], None] | None = None) -> str:
    """Delete exactly one currently eligible session and return its audit operation UUID.

    This private API never accepts a saved plan. An interrupted or partially failed
    operation has no resume path; a later call must pass fresh eligibility again.
    """
    if type(session_id) is not str or str(uuid.UUID(session_id)) != session_id:
        raise ValueError("retention target must be a canonical session UUID")
    scope = local_path(Path(root), directory=True)
    with acquire_lifecycle(scope, "retention") as lease:
        config = configuration_store.load()
        config.validate()
        fresh = plan_retention(scope, config, clock=clock, media_inspector=media_inspector)
        matches = [item for item in fresh["sessions"] if item["session_id"] == session_id]
        if len(matches) != 1 or matches[0]["classification"] != "eligible":
            raise ValueError("retention target is not uniquely and currently eligible")
        auth = authorize(scope, matches[0], config)
        check_policy(auth, configuration_store, clock())
        check_jobs(auth, job_paths)
        check_root(auth, frozenset())
        operation_id = str(uuid.uuid4())
        with RetentionAudit(scope, audit_path) as audit:
            # The intent is synced before any artifact is even attempted.
            audit.append("intent", operation_id, timestamp=clock(), root=str(scope),
                         session_id=session_id, creator=auth.creator,
                         ended_at=auth.ended_at, max_age_days=auth.max_age_days,
                         protected=False, protected_creators=list(auth.protected_creators),
                         artifacts=[item.audit_dict() for item in auth.order],
                         order=[item.relative_path for item in auth.order])
            deleted: set[str] = set()
            for item in auth.order:
                path = scope / item.relative_path
                try:
                    if before_mutation is not None:
                        before_mutation(path)
                    lease.assert_held()
                    check_policy(auth, configuration_store, clock())
                    check_jobs(auth, job_paths)
                    check_root(auth, frozenset(deleted))
                    audit.append("attempt", operation_id, path=item.relative_path)
                    # Journal fsync may be slow; repeat all authorization checks
                    # immediately after it, then the final no-follow path check.
                    lease.assert_held()
                    check_policy(auth, configuration_store, clock())
                    check_jobs(auth, job_paths)
                    check_root(auth, frozenset(deleted))
                    check_fingerprint(scope, item, auth.volume)
                    if item.kind == "directory":
                        if any(path.iterdir()):
                            raise ValueError("retention parts directory is not empty")
                        path.rmdir()
                    else:
                        path.unlink()
                    _sync_parent(path)
                    deleted.add(item.relative_path)
                    audit.append("deleted", operation_id, path=item.relative_path)
                except BaseException as error:
                    try:
                        audit.append("failed", operation_id, path=item.relative_path,
                                     error_type=type(error).__name__)
                    except BaseException:
                        pass  # Keep the first failure and stop; the journal may be unavailable.
                    raise
            audit.append("completed", operation_id, deleted_count=len(deleted))
        return operation_id


def _sync_parent(path: Path) -> None:
    """Publish a successful POSIX removal before journaling it as deleted."""
    if os.name != "nt":
        descriptor = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
