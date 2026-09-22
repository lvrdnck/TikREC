"""Render fixed JSON-safe automatic-recording status fields."""

from __future__ import annotations

from .automation_state import AutomationState


def automation_snapshot(
    admitted: dict,
    *,
    state: AutomationState,
    operational: bool,
    stopping: bool,
    blocked_reason: str | None,
    latest_cycle_count: int,
    cycle_results: dict[str, dict],
    selected_creators: list[str],
    started_recordings: list[dict],
) -> dict:
    """Return admission data enriched with current and latest-cycle automation facts."""
    snapshot = dict(admitted)
    single_selected = selected_creators[0] if len(selected_creators) == 1 else None
    single_started = started_recordings[0] if len(started_recordings) == 1 else {}
    snapshot["automation"] = {
        "operational": operational and not stopping,
        "blocked_reason": "service_shutting_down" if stopping else blocked_reason,
        "latest_cycle_count": latest_cycle_count,
        "selected_creators": list(selected_creators),
        "started_recordings": [dict(item) for item in started_recordings],
        # Legacy singular fields remain only when they describe the complete result.
        "selected_creator": single_selected,
        "started_creator": single_started.get("creator"),
        "started_session_id": single_started.get("session_id"),
        "started_output_path": single_started.get("output_path"),
    }
    cycle = admitted.get("cycle_count")
    consumed = state.consumed()
    snapshot["creators"] = [
        _status_item(
            item, cycle=cycle, consumed=consumed,
            operational=operational and not stopping,
            blocked_reason=("service_shutting_down" if stopping else blocked_reason),
            latest_cycle_count=latest_cycle_count, cycle_results=cycle_results,
        )
        for item in admitted.get("creators", [])
    ]
    return snapshot


def _status_item(
    item: dict,
    *,
    cycle: object,
    consumed: dict[str, str],
    operational: bool,
    blocked_reason: str | None,
    latest_cycle_count: int,
    cycle_results: dict[str, dict],
) -> dict:
    value = dict(item)
    creator = item.get("creator")
    consumed_room = consumed.get(creator)
    current = item.get("room_id") if item.get("state") == "live" else None
    result = cycle_results.get(creator) if cycle == latest_cycle_count else None
    if result is None:
        if not operational and current is not None:
            result = _result("blocked", blocked_reason)
        elif current is not None and consumed_room == current:
            result = _result("suppressed", "same_room_consumed")
        elif current is not None:
            result = _result("armed")
        else:
            result = _result("not_applicable")
    value["automation"] = {
        **result,
        "armed": operational and current is not None and consumed_room != current,
        "consumed_room_id": consumed_room,
    }
    return value


def _result(state: str, reason: str | None = None) -> dict:
    return {"state": state, "reason": reason}
