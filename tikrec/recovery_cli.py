"""CLI wiring and output for read-only recovery discovery and validation."""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from pathlib import Path
from typing import TextIO

from .recovery_discovery import (RecoveryCandidate, discover_recovery_candidates,
                                 safe_source_description)
from .recovery_validation import RecoveryValidation, validate_recovery_candidates
from .validation import validate_target
from .validation_report import ValidationResult


def add_recovery_command(subcommands) -> argparse.ArgumentParser:
    """Add bounded read-only recovery discovery and validation."""
    recover = subcommands.add_parser(
        "recover",
        help="inspect interrupted recordings without changing them",
        description=(
            "Inspect one TikREC parts directory, or the immediate *.parts directories "
            "inside ROOT. Discovery and optional validation are read-only."
        ),
    )
    recover.add_argument("scope", metavar="ROOT")
    recover.add_argument("--json", action="store_true", help="print structured results")
    recover.add_argument(
        "--validate", action="store_true", help="validate safe recovery candidates read-only"
    )
    return recover


def run_recovery_command(
    arguments,
    stdout: TextIO,
    *,
    discoverer: Callable[[Path], tuple[RecoveryCandidate, ...]] = discover_recovery_candidates,
    validator: Callable[..., ValidationResult] = validate_target,
) -> int:
    """Discover and report recovery candidates without altering their artifacts."""
    scope = Path(arguments.scope)
    candidates = discoverer(scope)
    validations = (
        validate_recovery_candidates(candidates, validator=validator)
        if arguments.validate else None
    )
    if arguments.json:
        document = {
            "scope": str(scope),
            "candidate_count": len(candidates),
            "candidates": [candidate.as_dict() for candidate in candidates],
        }
        if validations is not None:
            document["validation_requested"] = True
            for candidate, validation in zip(document["candidates"], validations):
                candidate["validation"] = validation.as_dict()
        print(json.dumps(document, indent=2, sort_keys=True), file=stdout)
        return _validation_exit_code(validations)
    print(render_recovery_report(scope, candidates, validations), file=stdout)
    return _validation_exit_code(validations)


def render_recovery_report(
    scope: Path,
    candidates: tuple[RecoveryCandidate, ...],
    validations: tuple[RecoveryValidation, ...] | None = None,
) -> str:
    """Render recovery facts for an owner who does not know TikREC internals."""
    if not candidates:
        message = f"No TikREC recovery candidates found in {scope}."
        return (
            f"{message}\nValidation was requested; nothing was validated."
            if validations is not None else message
        )
    lines = [f"Recovery candidates in {scope}: {len(candidates)}"]
    for number, candidate in enumerate(candidates, 1):
        output = candidate.output_path or "not declared"
        session = candidate.session_id or "unknown"
        lines.extend([
            "",
            f"{number}. {candidate.parts_directory}",
            f"   Session: {session}",
            f"   Source: {safe_source_description(candidate)}",
            f"   Intended output: {output}",
            f"   Session state: {candidate.lifecycle_state}",
            f"   Retained parts: {candidate.retained_parts}",
            f"   Final output: {candidate.final_output}",
            f"   Finalization: {candidate.finalization_state}",
            f"   Evidence consistent: {'yes' if candidate.evidence_consistent else 'no'}",
            f"   {'Discovery: ' if validations is not None else ''}{candidate.summary}",
        ])
        if validations is None:
            lines.append(f"   Next action: {candidate.next_action}")
        if candidate.untouched_reason is not None:
            lines.append(f"   Leave untouched because: {candidate.untouched_reason}")
        if validations is not None:
            _render_validation(lines, validations[number - 1])
    return "\n".join(lines)


def _render_validation(lines: list[str], validation: RecoveryValidation) -> None:
    lines.extend([
        "   Validation requested: yes",
        f"   Validation ran: {'yes' if validation.ran else 'no'}",
        f"   Validation result: {validation.status}",
        f"   {validation.summary}",
    ])
    for finding in validation.findings:
        lines.append(f"   - [{finding.code}] {finding.message}")
    if validation.omitted_findings:
        lines.append(f"   - {validation.omitted_findings} additional finding(s) omitted")
    lines.append(f"   Safest next action: {validation.next_action}")


def _validation_exit_code(validations: tuple[RecoveryValidation, ...] | None) -> int:
    if validations is None or all(validation.status == "passed" for validation in validations):
        return 0
    return 1
