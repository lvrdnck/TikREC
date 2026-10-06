"""Call-local authorization for the one explicit fresh restart-recovery owner."""

from threading import get_ident

from .session_journal_types import require


def authorize(journal, capability, kind, *arguments):
    """Reject recovered receipts and stale callers as native write permission."""
    from .release_recovery import ReleaseRecovery
    require(type(capability) is ReleaseRecovery and capability.journal is journal,
            'current explicit release recovery authority required')
    with capability.authority.lock:
        require(capability.authority._release_recovery is capability
                and capability.authority._recovery_owners.get(capability.token) is capability
                and capability.authority.recovery_gate._is_owned()
                and capability.call_thread == capability.execution_thread == get_ident()
                and capability.call_authority == (kind, *arguments),
                'current explicit release recovery authority required')
        if kind != 'record_release_recovery_cleanup':
            capability._check_cancelled()
        capability.authority.assert_held()
