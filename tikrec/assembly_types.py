"""Internal unpublished artifacts, process evidence and reachable cleanup owners."""

from dataclasses import dataclass
from pathlib import Path

from .finalize_plan import MediaPlan
from .owned_process_types import ProcessEvidence


@dataclass(frozen=True)
class AssemblyChild:
    """A child snapshot plus its exact owner for reconciliation after uncertainty."""

    phase: str
    command: tuple[str, ...]
    evidence: ProcessEvidence
    owner: object


@dataclass(frozen=True)
class UnpublishedCandidate:
    """Execution readiness only; never validated, published or session completion."""

    session_id: str | None
    attempt_token: str
    state: str
    candidate: Path | None
    work_scope: Path | None
    plan: MediaPlan | None
    children: tuple[AssemblyChild, ...]
    input_decode: dict
    diagnostics_complete: bool
    error: BaseException | None
    diagnostics: tuple[BaseException, ...]
    media_validation: str = "not_checked"
    publication: str = "unpublished"


class AssemblyCancelled(RuntimeError):
    """Irreversible caller cancellation; no automatic replacement attempt."""


class AssemblyError(RuntimeError):
    """Preserve the original failure, result and all reachable attempt controls."""

    def __init__(self, attempt, result):
        super().__init__(f"unpublished assembly {result.state}: {result.error}")
        self.attempt, self.result, self.original = attempt, result, result.error
        self.diagnostics = result.diagnostics
