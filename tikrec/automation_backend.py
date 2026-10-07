"""Optional journal-backend seams; existing controller behavior stays unchanged."""


def reconcile_pending(coordinator, claim):
    """Resolve persisted acceptance through an explicit backend when provided."""
    reconcile = getattr(coordinator._controller, 'reconcile_automatic_claim', None)
    if not callable(reconcile):
        return False
    try:
        accepted = reconcile(claim)
    except Exception:
        coordinator._disable('automation_state_ambiguous')
        return True
    consumed = coordinator._state.consumed()
    if accepted:
        consumed[claim.creator] = claim.room_id
    coordinator._replace_state(consumed, None, 'automation_state_ambiguous')
    return True


def accepted_start(controller, claim, page, raw):
    """Use opt-in acceptance binding or the unchanged legacy start call."""
    automatic = getattr(controller, 'start_automatic', None)
    if callable(automatic):
        return automatic(claim, raw_copy=raw)
    return controller.start(page, claim.output_path, expected_room_id=claim.room_id,
                            raw_copy=raw)
