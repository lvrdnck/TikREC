"""Call-local authorization for the one explicit fresh restart-recovery owner."""

from threading import get_ident

from .session_journal_types import require


def authorize(journal, capability, kind, *arguments):
    """Reject recovered receipts and stale callers as native write permission."""
    from .release_recovery import ReleaseRecovery
    require(type(capability) is ReleaseRecovery and capability.journal is journal
            and capability.authority._release_recovery is capability
            and capability.call_thread == get_ident()
            and capability.call_authority == (kind, *arguments)
            and capability.authority.lock._is_owned(),
            'current explicit release recovery authority required')
    capability.authority.assert_held()
