"""Internal one-session destructive retention with fresh bounded authorization."""

from __future__ import annotations

import time
import uuid
import os
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from .configuration import Configuration, ConfigurationStore
from .lifecycle_lock import acquire_lifecycle
from .media import MediaInfo, inspect_media
from .retention_audit import RetentionAudit
from .retention_authorization import (authorize, check_jobs,
                                      check_policy, check_root)
from .retention_mutation import (quarantine_relative, remove_authorized,
                                 require_identity_removal)
from .policy_lock import policy_lock
from .retention_paths import local_path
from .retention_plan import _plan_retention_with_snapshot


@dataclass
class RetentionProgress:
    """Caller-owned facts for classifying an operation across executor cleanup."""

    operation_id: str | None = None
    audit_path: Path | None = None
    intent_attempted: bool = False
    intent_sync_started: bool = False
    intent_durable: bool = False
    completed_durable: bool = False
    deleted_count: int = 0
    removal_uncertain: bool = False
    audit_uncertain: bool = False

    def mark_intent_sync_started(self) -> None:
        """Record the boundary after writing intent and before calling fsync."""
        self.intent_sync_started = True

    def mark_intent_durable(self) -> None:
        """Record a successful audit intent sync before append can return."""
        self.intent_durable = True

    def mark_completed_durable(self) -> None:
        """Publish proven completion before audit or lifecycle cleanup runs."""
        self.completed_durable = True


def execute_retention(root: Path, session_id: str, configuration_store: ConfigurationStore,
                      *, audit_path: Path | None = None,
                      job_paths: tuple[Path, Path] | None = None,
                      clock: Callable[[], float] = time.time,
                      media_inspector: Callable[[Path], MediaInfo | None] = inspect_media,
                      before_mutation: Callable[[Path], None] | None = None,
                      preview_guard: tuple | None = None,
                      progress: RetentionProgress | None = None) -> str:
    """Delete exactly one currently eligible session and return its audit operation UUID.

    This private API never accepts a saved plan. An interrupted or partially failed
    operation has no resume path; a later call must pass fresh eligibility again.
    """
    require_identity_removal()  # Unsupported systems refuse even before lock/audit creation.
    if type(session_id) is not str or str(uuid.UUID(session_id)) != session_id:
        raise ValueError("retention target must be a canonical session UUID")
    scope = local_path(Path(root), directory=True)
    progress = progress if progress is not None else RetentionProgress()
    with acquire_lifecycle(scope, "retention") as lease:
        auth, evidence, config = _fresh_authorization(
            scope, session_id, configuration_store, job_paths, clock, media_inspector)
        if preview_guard is not None and preview_guard != _preview_signature(
                auth, evidence, config):
            raise ValueError("retention evidence changed after deletion preview")

        @contextmanager
        def mutation_authority():
            with policy_lock(configuration_store.path) as policy:
                lease.assert_held()
                check_policy(auth, configuration_store, clock())
                check_jobs(auth, job_paths)
                policy.assert_held()
                yield

        operation_id = str(uuid.uuid4())
        with RetentionAudit(scope, audit_path) as audit:
            progress.operation_id, progress.audit_path = operation_id, audit.path
            # The intent is synced before any artifact is even attempted.
            progress.intent_attempted = True
            try:
                audit.append("intent", operation_id,
                             before_sync=progress.mark_intent_sync_started,
                             after_sync=progress.mark_intent_durable,
                             timestamp=clock(), root=str(scope),
                             session_id=session_id, creator=auth.creator,
                             ended_at=auth.ended_at, max_age_days=auth.max_age_days,
                             protected=False, protected_creators=list(auth.protected_creators),
                             target_controls={entry[0]: entry[2] for entry in
                                              auth.target_claim.evidence if len(entry) == 3
                                              and entry[2] is not None},
                             artifact_byte_hashes=dict(auth.artifact_byte_hashes),
                             recovery_byte_hashes=dict(auth.recovery_byte_hashes),
                             artifacts=[item.audit_dict() for item in auth.order],
                             order=[item.relative_path for item in auth.order],
                             quarantine_order=[quarantine_relative(item, operation_id, index)
                                               for index, item in enumerate(auth.order)])
            except BaseException:
                progress.audit_uncertain = True
                raise
            deleted: set[str] = set()
            hashes = dict(auth.artifact_byte_hashes)
            for index, item in enumerate(auth.order):
                path = scope / item.relative_path
                try:
                    if before_mutation is not None:
                        before_mutation(path)
                    lease.assert_held()
                    check_policy(auth, configuration_store, clock())
                    check_jobs(auth, job_paths)
                    check_root(auth, frozenset(deleted))
                    try:
                        audit.append("attempt", operation_id, path=item.relative_path)
                    except BaseException:
                        progress.audit_uncertain = True
                        raise
                    # Journal fsync may be slow; repeat all authorization checks
                    # immediately after it, then the final no-follow path check.
                    lease.assert_held()
                    check_policy(auth, configuration_store, clock())
                    check_jobs(auth, job_paths)
                    check_root(auth, frozenset(deleted))
                    progress.removal_uncertain = True
                    remove_authorized(scope, item, auth.volume,
                                      hashes.get(item.relative_path),
                                      operation_id, index, _sync_parent, mutation_authority)
                    progress.removal_uncertain = False
                    deleted.add(item.relative_path)
                    progress.deleted_count = len(deleted)
                    try:
                        audit.append("deleted", operation_id, path=item.relative_path)
                    except BaseException:
                        progress.audit_uncertain = True
                        raise
                except BaseException as error:
                    try:
                        audit.append("failed", operation_id, path=item.relative_path,
                                     error_type=type(error).__name__)
                    except BaseException:
                        progress.audit_uncertain = True
                        # Keep the first failure and stop; the journal may be unavailable.
                    raise
            try:
                audit.append("completed", operation_id,
                             after_sync=progress.mark_completed_durable,
                             deleted_count=len(deleted))
            except BaseException:
                progress.audit_uncertain = True
                raise
        return operation_id


def _fresh_authorization(scope: Path, session_id: str,
                         configuration_store: ConfigurationStore,
                         job_paths: tuple[Path, Path] | None,
                         clock: Callable[[], float], media_inspector: Callable):
    """Rebuild complete private authority; a preview may only compare against it."""
    config = configuration_store.load()
    config.validate()
    fresh, evidence, first_bytes = _plan_retention_with_snapshot(
        scope, config, clock=clock, media_inspector=media_inspector, bind_bytes=True)
    matches = [item for item in fresh["sessions"] if item["session_id"] == session_id]
    if len(matches) != 1 or matches[0]["classification"] != "eligible":
        raise ValueError("retention target is not uniquely and currently eligible")
    auth = authorize(scope, matches[0], config, evidence,
                     first_bytes.get(matches[0]["parts_directory"], ()))
    # A second coherent observation closes the plan-to-authority gap.
    confirmed, closing, closing_bytes = _plan_retention_with_snapshot(
        scope, config, clock=clock, media_inspector=media_inspector, bind_bytes=True)
    if confirmed != fresh or closing != evidence or closing_bytes != first_bytes:
        raise ValueError("retention eligibility changed before authorization")
    check_policy(auth, configuration_store, clock())
    check_jobs(auth, job_paths)
    check_root(auth, frozenset())
    return auth, evidence, config


def _preview_signature(auth, evidence, config: Configuration) -> tuple:
    """Bind displayed authority facts without making a saved plan executable."""
    # First-use lease creation can change root directory timestamps without
    # changing any retention claimant; the root object and all claims stay bound.
    return (auth.root, auth.root_identity, auth.volume, evidence.claims,
            evidence.stable,
            config.retention_max_age_days, config.retention_protected_creators,
            auth.session_id, auth.creator, auth.ended_at, auth.output, auth.parts,
            auth.order, auth.artifact_byte_hashes, auth.recovery_byte_hashes)


def _sync_parent(path: Path) -> None:
    """Publish a successful POSIX removal before journaling it as deleted."""
    if os.name != "nt":
        descriptor = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
