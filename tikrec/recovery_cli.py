"""CLI wiring and output for guided recovery discovery, validation, and finalization."""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from pathlib import Path
from typing import TextIO

from .recovery_discovery import (RecoveryCandidate, discover_recovery_candidates,
                                 safe_source_description)
from .recovery_finalization import (RecoveryFinalization, guided_finalize)
from .recovery_validation import RecoveryValidation, validate_recovery_candidates
from .finalize import finalize_parts
from .validation import validate_target
from .validation_report import ValidationResult


def add_recovery_command(subcommands) -> argparse.ArgumentParser:
    """Add bounded recovery discovery, validation, and explicit finalization."""
    recover = subcommands.add_parser(
        "recover",
        help="inspect or explicitly finalize an interrupted recording",
        description=(
            "Inspect one TikREC parts directory, or the immediate *.parts directories "
            "inside ROOT. Discovery and optional validation are read-only; --finalize "
            "requires one explicit session directory and may update it."
        ),
    )
    recover.add_argument("scope", metavar="ROOT")
    recover.add_argument("--json", action="store_true", help="print structured results")
    recover.add_argument(
        "--validate", action="store_true", help="validate safe recovery candidates read-only"
    )
    recover.add_argument(
        "--finalize", action="store_true",
        help="validate and finalize one explicitly named recoverable session",
    )
    return recover


def run_recovery_command(
    arguments,
    stdout: TextIO,
    *,
    discoverer: Callable[[Path], tuple[RecoveryCandidate, ...]] = discover_recovery_candidates,
    validator: Callable[..., ValidationResult] = validate_target,
    finalizer: Callable[..., Path] = finalize_parts,
) -> int:
    """Discover and optionally validate or explicitly finalize recovery evidence."""
    scope = Path(arguments.scope)
    candidates = discoverer(scope)
    finalization: RecoveryFinalization | None = None
    if arguments.finalize:
        progress = None if arguments.json else lambda message: print(
            f"Recovery: {message}", file=stdout
        )
        validations, finalization = guided_finalize(
            scope, candidates, discoverer=discoverer, validator=validator,
            finalizer=finalizer, progress=progress,
        )
    else:
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
        if validations is not None or arguments.finalize:
            document["validation_requested"] = True
        if validations is not None:
            for candidate, validation in zip(document["candidates"], validations):
                candidate["validation"] = validation.as_dict()
        if finalization is not None:
            document["guided_finalization"] = finalization.as_dict()
        print(json.dumps(document, indent=2, sort_keys=True), file=stdout)
        return _exit_code(validations, finalization)
    report = render_recovery_report(scope, candidates, validations)
    if finalization is not None:
        report = f"{report}\n\n{render_finalization(finalization)}"
    print(report, file=stdout)
    return _exit_code(validations, finalization)


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


def render_finalization(finalization: RecoveryFinalization) -> str:
    """Render one guided-finalization result in plain language."""
    lines = [
        "Guided finalization:",
        f"   Attempted: {'yes' if finalization.attempted else 'no'}",
        f"   Result: {finalization.status}",
        f"   {finalization.summary}",
    ]
    if finalization.reason is not None:
        lines.append(f"   Reason: {finalization.reason}")
    return "\n".join(lines)


def _exit_code(
    validations: tuple[RecoveryValidation, ...] | None,
    finalization: RecoveryFinalization | None,
) -> int:
    if finalization is not None:
        if finalization.status == "interrupted":
            return 130
        return 0 if finalization.succeeded else 1
    if validations is None or all(validation.status == "passed" for validation in validations):
        return 0
    return 1
