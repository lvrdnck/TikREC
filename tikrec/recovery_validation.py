"""Guided read-only validation for safely discovered recovery candidates."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path

from .recovery_discovery import RecoveryCandidate
from .validation import validate_target
from .validation_report import ValidationFinding, ValidationResult


_MAX_FINDINGS = 5
_VALIDATABLE = {"recoverable", "complete"}


@dataclass(frozen=True)
class RecoveryValidation:
    """Structured outcome of optional validation for one recovery candidate."""

    requested: bool
    ran: bool
    status: str
    passed: bool | None
    summary: str
    next_action: str
    parts_checked: int
    media_integrity: str
    session_completeness: str
    output_availability: str
    finding_count: int
    findings: tuple[ValidationFinding, ...]
    omitted_findings: int

    def as_dict(self) -> dict[str, object]:
        """Return stable JSON-ready validation facts."""
        values = asdict(self)
        values["findings"] = [asdict(finding) for finding in self.findings]
        return values


def validate_recovery_candidates(
    candidates: tuple[RecoveryCandidate, ...],
    *,
    validator: Callable[..., ValidationResult] = validate_target,
) -> tuple[RecoveryValidation, ...]:
    """Validate only candidates whose discovery state is safely inspectable."""
    return tuple(_validate_candidate(candidate, validator) for candidate in candidates)


def _validate_candidate(candidate, validator):
    if not candidate.evidence_consistent or candidate.classification not in _VALIDATABLE:
        return _skipped(candidate)
    try:
        result = validator(Path(candidate.parts_directory), deep=False)
        if not isinstance(result, ValidationResult):
            raise TypeError("validator returned an unsupported result")
        if (result.target_type != "session"
                or Path(result.target).resolve() != Path(candidate.parts_directory).resolve()):
            raise ValueError("validation no longer describes the discovered session")
    except Exception as error:
        finding = ValidationFinding(
            "error", "validation_exception",
            f"validation could not complete ({type(error).__name__})",
            candidate.parts_directory,
        )
        return RecoveryValidation(
            True, True, "failed", False,
            "Validation could not complete safely — TikREC left everything untouched.",
            "Preserve the artifacts and resolve the validation failure before finalization.",
            0, "not_checked", candidate.lifecycle_state, candidate.final_output,
            1, (finding,), 0,
        )
    findings, omitted = _concise_findings(result.findings)
    if result.passed:
        next_action = (
            "Final output already exists; no recovery action is needed."
            if candidate.classification == "complete"
            else "Manual tikrec finalize is available; no action was performed."
        )
        summary = "Validation passed — retained recording parts appear usable for recovery."
        status = "passed"
    else:
        next_action = "Preserve the artifacts and review validation findings before finalization."
        summary = (
            "Validation found problems — TikREC will not recommend finalization automatically."
        )
        status = "failed"
    return RecoveryValidation(
        True, True, status, result.passed, summary, next_action,
        result.parts_checked, result.media_integrity, result.session_completeness,
        result.output_availability, len(result.findings), findings, omitted,
    )


def _skipped(candidate: RecoveryCandidate) -> RecoveryValidation:
    if candidate.classification == "active_or_uncertain":
        summary = "This session may still be active — validation was skipped."
    else:
        summary = "Evidence is incomplete or conflicting — TikREC left everything untouched."
    return RecoveryValidation(
        True, False, "skipped", None, summary, candidate.next_action,
        0, "not_checked", candidate.lifecycle_state, candidate.final_output,
        0, (), 0,
    )


def _concise_findings(
    findings: tuple[ValidationFinding, ...],
) -> tuple[tuple[ValidationFinding, ...], int]:
    ordered = tuple(finding for level in ("error", "warning")
                    for finding in findings if finding.level == level)
    selected = ordered[:_MAX_FINDINGS]
    return selected, max(0, len(findings) - len(selected))
