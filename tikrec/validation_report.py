"""Stable human and JSON result models for recording validation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class ValidationFinding:
    """One stable, machine-readable validation error or warning."""

    level: str
    code: str
    message: str
    path: str | None = None


@dataclass(frozen=True)
class ValidationResult:
    """Collected validation facts for one user-supplied target."""

    target: str
    target_type: str
    deep: bool
    passed: bool
    media_integrity: str
    session_completeness: str
    output_availability: str
    parts_checked: int
    findings: tuple[ValidationFinding, ...]

    def as_dict(self) -> dict[str, Any]:
        """Return the stable JSON representation used by ``--json``."""
        values = asdict(self)
        values["findings"] = [asdict(finding) for finding in self.findings]
        return values


def render_validation(result: ValidationResult) -> str:
    """Render a concise human report without hiding collected failures."""
    lines = [
        f"Validation {'passed' if result.passed else 'failed'}: {result.target}",
        f"Target: {result.target_type}",
        f"Validation mode: {'deep' if result.deep else 'standard'}",
        f"Media integrity: {result.media_integrity}",
        f"Session completeness: {result.session_completeness}",
        f"Output availability: {result.output_availability}",
        f"Parts checked: {result.parts_checked}",
    ]
    for level in ("error", "warning"):
        selected = [finding for finding in result.findings if finding.level == level]
        if selected:
            lines.append(f"{level.title()}s:")
            lines.extend(f"- {_finding_text(finding)}" for finding in selected)
    return "\n".join(lines)


def _finding_text(finding: ValidationFinding) -> str:
    location = f" ({finding.path})" if finding.path is not None else ""
    return f"[{finding.code}] {finding.message}{location}"
