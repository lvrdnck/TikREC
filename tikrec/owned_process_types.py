"""Internal process evidence, deliberately distinct from journal/media success proof."""

from dataclasses import dataclass
from uuid import UUID


def uuid_key(value):
    """Require explicit canonical UUIDs rather than deriving launch authority from a token."""
    if type(value) is not str or str(UUID(value)) != value:
        raise ValueError("explicit canonical session/attempt UUID required")
    return value


@dataclass(frozen=True)
class ProcessIdentity:
    """Attempt-bound native root identity; the retained handle supplies operational authority."""
    session_id: str
    attempt_token: str
    pid: int
    created: int
    image: str


@dataclass(frozen=True)
class ProcessEvidence:
    """Whole-job lifetime and bounded stream diagnostics, never media completion."""
    session_id: str
    attempt_token: str
    state: str
    identity: ProcessIdentity | None
    root_exit_code: int | None
    active_processes: int | None
    stdout: bytes
    stderr: bytes
    truncated: tuple[int, int]
    cancel_requested: bool
    error: BaseException | None
    diagnostics: tuple[BaseException, ...]
    diagnostics_dropped: int = 0


class ProcessOwnerError(RuntimeError):
    """First operational failure plus subsequent cleanup evidence and native exit state."""

    def __init__(self, evidence):
        super().__init__("owned child operation failed; inspect native lifetime evidence")
        self.evidence, self.original = evidence, evidence.error
        self.diagnostics = evidence.diagnostics
