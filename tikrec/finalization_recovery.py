"""Conservatively settle the exact encoder artifact left by a service crash."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .finalize import _temporary_output_path


@dataclass(frozen=True)
class FinalizationPartial:
    """An exact encoder artifact and its unused evidence destination."""

    temporary: Path
    preserved: Path


def preserved_partial_path(output: Path, session_id: str) -> Path:
    """Return the deterministic evidence path for one incomplete encoder output."""
    output = Path(output)
    suffix = output.suffix
    stem = output.name[: -len(suffix)]
    # Keep the container suffix last so operators can still probe preserved evidence.
    return output.with_name(f".{stem}.interrupted-{session_id}.partial{suffix}")


def plan_finalization_partial(
    output: Path,
    session_id: str,
    *,
    job_state: str,
    finalization_status: str,
) -> FinalizationPartial | None:
    """Validate a proven crash partial without changing any recovery evidence."""
    output = Path(output)
    temporary = _temporary_output_path(output)
    if not temporary.exists() and not temporary.is_symlink():
        return None
    if output.exists() or output.is_symlink():
        raise ValueError("output and encoder partial coexist; preserve both")
    if job_state != "finalizing" or finalization_status != "running":
        raise ValueError("encoder partial lacks finalization-in-progress evidence")
    if temporary.is_symlink() or not temporary.is_file() or temporary.stat().st_size == 0:
        raise ValueError("encoder partial is not a nonempty regular file")
    preserved = preserved_partial_path(output, session_id)
    if preserved.exists() or preserved.is_symlink():
        raise ValueError("preserved encoder evidence path already exists")
    return FinalizationPartial(temporary, preserved)


def preserve_finalization_partial(plan: FinalizationPartial) -> Path:
    """Atomically preserve a checked partial before re-encoding every retained part."""
    if (plan.temporary.is_symlink() or not plan.temporary.is_file()
            or plan.temporary.stat().st_size == 0):
        raise ValueError("encoder partial changed after inspection")
    if plan.preserved.exists() or plan.preserved.is_symlink():
        raise ValueError("finalization recovery destination already exists")
    # The owning service is single-process; atomic replacement closes the crash window
    # without ever exposing a copied half-file at the destination.
    os.replace(plan.temporary, plan.preserved)
    if plan.preserved.is_symlink() or not plan.preserved.is_file():
        raise OSError("finalization recovery could not publish a regular file")
    return plan.preserved
