"""Explicit single-session finalization for validated recovery evidence."""

from __future__ import annotations

import hashlib
import stat
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .finalize import _temporary_output_path, finalize_parts
from .manifest import SessionManifest
from .recovery_discovery import RecoveryCandidate
from .recovery_validation import RecoveryValidation, validate_recovery_candidates
from .session_parts import discover_parts
from .validation import validate_target
from .validation_report import ValidationResult


@dataclass(frozen=True)
class RecoveryEvidenceSnapshot:
    """Change-sensitive facts captured before expensive media validation."""

    manifest_sha256: str
    artifacts: tuple[tuple[str, int, int, int], ...]
    output_state: str
    temporary_output_state: str


@dataclass(frozen=True)
class RecoveryFinalization:
    """Structured result of one explicitly requested guided finalization."""

    requested: bool
    attempted: bool
    status: str
    succeeded: bool
    output_path: str | None
    retained_parts: int
    validation_before: str
    validation_after: str
    summary: str
    reason: str | None

    def as_dict(self) -> dict[str, object]:
        """Return stable JSON-ready guided-finalization facts."""
        return asdict(self)


def guided_finalize(
    scope: Path,
    candidates: tuple[RecoveryCandidate, ...],
    *,
    discoverer: Callable[[Path], tuple[RecoveryCandidate, ...]],
    validator: Callable[..., ValidationResult] = validate_target,
    finalizer: Callable[..., Path] = finalize_parts,
    progress: Callable[[str], None] | None = None,
) -> tuple[tuple[RecoveryValidation, ...] | None, RecoveryFinalization]:
    """Validate and finalize exactly one explicitly named recovery session."""
    candidate, refusal = _specific_candidate(Path(scope), candidates)
    if refusal is not None:
        return None, refusal
    assert candidate is not None
    try:
        snapshot = _snapshot(candidate)
        output = _safe_output(candidate)
    except (OSError, ValueError) as error:
        return None, _refused(candidate, str(error))

    validations = validate_recovery_candidates((candidate,), validator=validator)
    validation = validations[0]
    if validation.status != "passed":
        return validations, _refused(
            candidate, "standard validation did not pass", validation_before=validation.status
        )

    try:
        current, = discoverer(Path(scope))
        if current != candidate:
            raise ValueError("session evidence changed after validation")
        if _snapshot(current) != snapshot:
            raise ValueError("session artifacts changed after validation")
        # Resolve output safety again at the last read-only boundary before mutation.
        if _safe_output(current) != output:
            raise ValueError("declared output changed after validation")
        retained = discover_parts(Path(current.parts_directory)).parts
        manifest = SessionManifest.load(Path(current.parts_directory) / "session.json")
        if manifest is None or _snapshot(current) != snapshot:
            raise ValueError("session manifest changed before finalization")
    except (OSError, ValueError, TypeError) as error:
        return validations, _refused(
            candidate, str(error), validation_before=validation.status
        )

    try:
        manifest.mark_recovery(output, retained)
    except (OSError, ValueError) as error:
        return validations, _refused(
            candidate, f"recovery state could not be recorded ({type(error).__name__})",
            validation_before=validation.status,
        )

    try:
        if progress is not None:
            progress(f"finalizing {len(retained)} retained part(s)")
        produced = (
            finalizer(retained, output, progress=progress)
            if finalizer is finalize_parts else finalizer(retained, output)
        )
        _verify_produced_output(output, produced)
    except KeyboardInterrupt:
        _finish(manifest, retained, "interrupted", error="guided finalization interrupted")
        return validations, RecoveryFinalization(
            True, True, "interrupted", False, str(output), len(retained),
            validation.status, "not_run",
            "Recovery was interrupted — retained parts remain available.",
            "guided finalization was interrupted",
        )
    except Exception as error:
        reason = f"guided finalization failed ({type(error).__name__})"
        _finish(manifest, retained, "failed", error=reason)
        return validations, RecoveryFinalization(
            True, True, "failed", False, str(output), len(retained),
            validation.status, "not_run",
            "Recovery failed — original retained parts remain available.", reason,
        )

    try:
        manifest.finish_recovery(retained, "completed", output_path=output)
        result = validator(Path(candidate.parts_directory), deep=False)
        _require_post_validation(candidate, result, len(retained))
    except Exception as error:
        reason = f"recovered output validation failed ({type(error).__name__})"
        _finish(manifest, retained, "failed", output_path=output, error=reason)
        return validations, RecoveryFinalization(
            True, True, "failed", False, str(output), len(retained),
            validation.status, "failed",
            "Recovery produced an output, but verification failed — "
            "retained parts remain available.",
            reason,
        )
    return validations, RecoveryFinalization(
        True, True, "completed", True, str(output), len(retained),
        validation.status, "passed",
        f"Recovery completed — recovered recording written to {output}", None,
    )


def _specific_candidate(scope, candidates):
    if len(candidates) != 1:
        return None, _refused(None, "choose one specific TikREC session directory")
    candidate = candidates[0]
    try:
        if Path(candidate.parts_directory).resolve(strict=True) != scope.resolve(strict=True):
            return None, _refused(
                None, "choose the specific *.parts session directory, not its parent root"
            )
    except OSError:
        return None, _refused(None, "the requested session directory is unavailable")
    if candidate.classification != "recoverable" or not candidate.evidence_consistent:
        return candidate, _refused(candidate, "session is not safely recoverable")
    return candidate, None


def _snapshot(candidate: RecoveryCandidate) -> RecoveryEvidenceSnapshot:
    directory = Path(candidate.parts_directory)
    manifest = directory / "session.json"
    artifacts = []
    for path in sorted(directory.iterdir(), key=lambda item: item.name):
        if path.is_symlink():
            raise ValueError("symlinked session artifacts cannot be finalized safely")
        details = path.stat()
        artifacts.append((path.name, details.st_mode, details.st_size, details.st_mtime_ns))
    return RecoveryEvidenceSnapshot(
        hashlib.sha256(manifest.read_bytes()).hexdigest(), tuple(artifacts),
        _path_state(Path(candidate.output_path)) if candidate.output_path else "undeclared",
        (_path_state(_temporary_output_path(Path(candidate.output_path)))
         if candidate.output_path else "undeclared"),
    )


def _safe_output(candidate: RecoveryCandidate) -> Path:
    if candidate.output_path is None:
        raise ValueError(
            "session has no declared output path; use manual tikrec finalize --output FILE"
        )
    output = Path(candidate.output_path)
    if output.exists() or output.is_symlink():
        raise ValueError("declared final output already exists")
    temporary = _temporary_output_path(output)
    if temporary.exists() or temporary.is_symlink():
        raise ValueError("unsafe temporary finalization output already exists")
    if not output.parent.is_dir():
        raise ValueError("declared output directory does not exist")
    for parent in (output.parent, *output.parent.parents):
        if parent.is_symlink():
            raise ValueError("symlinked output directories cannot be finalized safely")
    return output


def _path_state(path: Path) -> str:
    if path.is_symlink():
        return "symlink"
    if not path.exists():
        return "missing"
    details = path.stat()
    kind = "file" if stat.S_ISREG(details.st_mode) else "other"
    return f"{kind}:{details.st_size}:{details.st_mtime_ns}"


def _verify_produced_output(expected: Path, produced: Any) -> None:
    actual = Path(produced)
    if actual.resolve() != expected.resolve():
        raise ValueError("finalizer returned a different output path")
    if actual.is_symlink() or not actual.is_file() or actual.stat().st_size == 0:
        raise ValueError("finalizer did not produce a non-empty regular output")


def _require_post_validation(candidate, result, retained_parts):
    if not isinstance(result, ValidationResult):
        raise TypeError("validator returned an unsupported result")
    if (result.target_type != "session"
            or Path(result.target).resolve() != Path(candidate.parts_directory).resolve()):
        raise ValueError("validation no longer describes the recovered session")
    if (not result.passed or result.output_availability != "present"
            or result.parts_checked != retained_parts):
        raise ValueError("recovered session did not pass standard validation")


def _finish(manifest, retained, status, *, output_path=None, error=None):
    try:
        manifest.finish_recovery(retained, status, output_path=output_path, error=error)
    except (OSError, ValueError):
        # The CLI still reports failure; the prior atomic running state remains honest.
        pass


def _refused(candidate, reason, *, validation_before="not_run"):
    return RecoveryFinalization(
        True, False, "refused", False,
        None if candidate is None else candidate.output_path,
        0 if candidate is None else candidate.retained_parts,
        validation_before, "not_run",
        "TikREC did not modify the session.", reason,
    )
