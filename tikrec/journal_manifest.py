"""Internal connected manifest completion without settlement, scheduler or release."""

from .journal_publication import JournalPublication, PublicationError
from .manifest_completion import ManifestCompletion
from .session_journal_types import require


class ManifestCompletionError(RuntimeError):
    """Expose first failure and every exact possibly-live control owner."""

    def __init__(self, adapter, original):
        super().__init__('manifest completion failed or ambiguous; all ownership retained')
        self.adapter, self.original = adapter, original
        self.diagnostics = tuple(adapter.coordinator.errors)
        self.diagnostics_dropped = adapter.coordinator.errors_dropped


class JournalManifest:
    """One original acquisition path, selected explicitly before input protection."""

    def __init__(self, authority, **options):
        self.publication = JournalPublication(authority, manifest_completion=True, **options)
        self.coordinator = self.publication.coordinator
        self.capability, self.error, self.used = None, None, False

    def run(self):
        """Complete at most one exact FIFO session's manifest and retain its task."""
        with self.coordinator.run_lock:
            require(not self.used, 'manifest adapter is single-use')
            self.used = True
            try:
                if self.publication.run() is None:
                    return None
                self.capability = ManifestCompletion(self.publication)
                return self.capability.complete()
            except BaseException as original:
                self.capability = getattr(self.coordinator, 'manifest_owner', self.capability)
                self.error = original.original if isinstance(original, PublicationError) else original
                runner = self.coordinator
                runner.cancelled.set()
                if runner.scratch is not None:
                    runner.validation_retained = True
                    runner.scratch.hold(self.error)
                raise ManifestCompletionError(self, self.error) from self.error

    def cancel(self, timeout=5):
        """Fence new control writes and cancel only the exact owned child."""
        return self.coordinator.cancel(timeout)

    def close(self, timeout=5):
        """Revoke execution; truthful cleanup remains incomplete while controls are retained."""
        return self.coordinator.close(timeout)
