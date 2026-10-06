"""Explicit complete internal success lifecycle; standalone and earlier adapters stay unchanged."""

from .journal_manifest import JournalManifest, ManifestCompletionError
from .owned_settlement import OwnedSettlement
from .session_journal_types import require


class SettlementError(RuntimeError):
    """Preserve first failure and exact retained resources without recreating authority."""

    def __init__(self, adapter, original):
        super().__init__('success release failed or ambiguous; inspect committed accounting and cleanup')
        self.adapter, self.original = adapter, original
        self.diagnostics = tuple(adapter.coordinator.errors)
        self.diagnostics_dropped = adapter.coordinator.errors_dropped


class JournalSettlement:
    """One explicitly invoked FIFO session through manifest completion and safe settlement."""

    def __init__(self, authority, **options):
        self.manifest = JournalManifest(authority, **options)
        self.coordinator = self.manifest.coordinator
        self.coordinator.settlement_capable = True
        self.capability, self.error, self.used = None, None, False

    def run(self):
        """Complete at most one original owned attempt, returning capacity only after cleanup."""
        with self.coordinator.run_lock:
            require(not self.used, 'success lifecycle adapter is single-use')
            self.used = True
            try:
                if self.manifest.run() is None:
                    return None
                self.capability = OwnedSettlement(self.manifest)
                return self.capability.complete()
            except BaseException as original:
                self.error = original.original if isinstance(original, ManifestCompletionError) else original
                self.coordinator.cancelled.set()
                raise SettlementError(self, self.error) from self.error

    def cancel(self, timeout=5):
        """Cancel before preparation; thereafter only prepared cleanup/accounting can continue."""
        return self.coordinator.cancel(timeout)

    def close(self, timeout=5):
        """Report exact cleanup without retrying a consumed native or release operation."""
        if self.capability is not None and self.capability.operation is not None:
            return self.capability.evidence()['cleanup_complete']
        return self.coordinator.close(timeout)

    def cleanup_evidence(self):
        """Expose pending cleanup and terminal settlement as separate facts."""
        return self.coordinator.cleanup_evidence() if self.capability is None else self.capability.evidence()
