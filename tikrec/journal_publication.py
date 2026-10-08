"""Internal one-shot assembly/validation/publication with continuously held owners."""

from .candidate_publication import CandidatePublication
from .journal_validation import JournalValidation, ValidationError
from .session_journal_types import require


class PublicationError(RuntimeError):
    """Keep the first failure and exact possibly-transitioned owners reachable."""

    def __init__(self, adapter, original):
        super().__init__("publication failed or ambiguous; ownership retained")
        self.adapter, self.original = adapter, original
        self.diagnostics = tuple(adapter.coordinator.errors)


class JournalPublication:
    """Explicit original-acquisition capability; no scheduler, recovery or settlement."""

    def __init__(self, authority, **options):
        self.validation = JournalValidation(authority, candidate_publication=True, **options)
        self.coordinator = self.validation.coordinator
        self.capability, self.error, self.used = None, None, False

    def run(self):
        """Publish at most one FIFO session, keeping original evidence and all pins."""
        with self.coordinator.run_lock:
            require(not self.used, "publication adapter is single-use")
            self.used = True
            try:
                if self.validation.run() is None:
                    return None
                self.capability = CandidatePublication(self.validation)
                return self.capability.promote()
            except BaseException as original:
                self.error = original.original if isinstance(original, ValidationError) else original
                runner = self.coordinator
                runner.cancelled.set()
                if runner.scratch is not None:
                    # Only the known pilot byte refusal sealed unpublished bytes before
                    # any validator existed; its ordinary original-owner cleanup is safe.
                    runner.validation_retained = not getattr(runner, 'pilot_candidate_refused', False)
                    runner.scratch.hold(self.error)
                raise PublicationError(self, self.error) from self.error

    def cancel(self, timeout=5):
        """Fence publication and bound cancellation of only the exact owned child."""
        return self.coordinator.cancel(timeout)

    def close(self, timeout=5):
        """Revoke execution and clean proven child controls, retaining evidence pins."""
        return self.coordinator.close(timeout)
