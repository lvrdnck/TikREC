"""Narrow original live success capability; journal history never reconstructs permission."""

from threading import get_ident

from .session_journal_types import require


def authorize(journal, capability, kind, token, owner, revision, value):
    """Bind a journal write to the one current local call and its owning thread."""
    from .owned_settlement import OwnedSettlement
    require(type(capability) is OwnedSettlement and capability.runner.journal is journal
            and capability.runner.settlement_owner is capability
            and capability.manifest is capability.runner.manifest_adapter
            and capability.manifest.error is None
            and capability.call_thread == get_ident()
            and capability.call_authority == (kind, token, owner, revision, value),
            'original live release continuation required')
