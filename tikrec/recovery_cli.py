"""CLI wiring and plain-language output for read-only recovery discovery."""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from pathlib import Path
from typing import TextIO

from .recovery_discovery import (RecoveryCandidate, discover_recovery_candidates,
                                 safe_source_description)


def add_recovery_command(subcommands) -> argparse.ArgumentParser:
    """Add the bounded read-only recovery discovery command."""
    recover = subcommands.add_parser(
        "recover",
        help="inspect interrupted recordings without changing them",
        description=(
            "Inspect one TikREC parts directory, or the immediate *.parts directories "
            "inside ROOT. This first recovery step is read-only."
        ),
    )
    recover.add_argument("scope", metavar="ROOT")
    recover.add_argument("--json", action="store_true", help="print structured results")
    return recover


def run_recovery_command(
    arguments,
    stdout: TextIO,
    *,
    discoverer: Callable[[Path], tuple[RecoveryCandidate, ...]] = discover_recovery_candidates,
) -> int:
    """Discover and report recovery candidates without altering their artifacts."""
    scope = Path(arguments.scope)
    candidates = discoverer(scope)
    if arguments.json:
        document = {
            "scope": str(scope),
            "candidate_count": len(candidates),
            "candidates": [candidate.as_dict() for candidate in candidates],
        }
        print(json.dumps(document, indent=2, sort_keys=True), file=stdout)
        return 0
    print(render_recovery_report(scope, candidates), file=stdout)
    return 0


def render_recovery_report(
    scope: Path, candidates: tuple[RecoveryCandidate, ...]
) -> str:
    """Render recovery facts for an owner who does not know TikREC internals."""
    if not candidates:
        return f"No TikREC recovery candidates found in {scope}."
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
            f"   {candidate.summary}",
            f"   Next action: {candidate.next_action}",
        ])
        if candidate.untouched_reason is not None:
            lines.append(f"   Leave untouched because: {candidate.untouched_reason}")
    return "\n".join(lines)
