"""Session-bound public LIVE ownership facts for manager allocation."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from .recording_safety import normalize_live_url
from .tiktok_identity import canonical_room_id


@dataclass(frozen=True)
class CurrentOwner:
    """One current slot's stable public identity, without transport data."""

    session_id: str
    page: str
    room_id: str | None


class OwnerCache:
    """Retain proven page/room facts until settlement or session replacement."""

    def __init__(self) -> None:
        self._owners: dict[str, CurrentOwner] = {}

    def get(self, slot_id: str) -> CurrentOwner | None:
        """Return the current in-memory claim for a stable manager slot."""
        return self._owners.get(slot_id)

    def claim(self, slot_id: str, session_id: str, page: str,
              expected_room: str | None) -> None:
        """Reserve an accepted start before its worker can publish identity."""
        self._owners[slot_id] = CurrentOwner(session_id, page, expected_room)

    def refresh(self, slot_id: str, controller: object, status: dict,
                health: dict, status_current: bool) -> bool:
        """Merge narrow/current facts; report when allocation must fail closed."""
        readable = status.get("state") != "unavailable"
        uncertain = False
        incomplete = False
        if readable and status_current:
            facts = _facts(status)
            uncertain = self._merge(slot_id, facts) if facts else True

        snapshot = _snapshot(controller)
        if snapshot is not None and type(snapshot.get("current")) is bool:
            if snapshot["current"]:
                facts = _facts(snapshot)
                if facts is not None:
                    # A later controller-lock read can add a newly proven room.
                    return self._merge(slot_id, facts)
                prior = self._owners.get(slot_id)
                if (prior is not None and snapshot.get("session_id") is not None
                        and snapshot.get("session_id") != prior.session_id):
                    # A partial new session must never inherit the old claim.
                    return True
                incomplete = True
            elif health.get("active") is not True:
                self._owners.pop(slot_id, None)
                return False
            else:
                return True

        if incomplete:
            # A later current read with invalid identity cannot prove the old
            # session still owns this slot or that a readable idle state won.
            return True
        if readable and not status_current:
            self._owners.pop(slot_id, None)
            return False
        owner = self._owners.get(slot_id)
        if readable:
            return uncertain or (status_current and owner is None)
        if owner is not None:
            # A page-only claim cannot rule out a room learned during failed reads.
            return owner.room_id is None
        # Only affirmative availability proves emptiness when both identity
        # reads fail; ambiguous recovery and failed health reads do not.
        return health.get("active") is True or health.get("available") is not True

    def _merge(self, slot_id: str, facts: CurrentOwner) -> bool:
        prior = self._owners.get(slot_id)
        if prior is not None and prior.session_id == facts.session_id:
            if prior.page != facts.page or (
                prior.room_id is not None and facts.room_id is not None
                and prior.room_id != facts.room_id
            ):
                return True
            facts = CurrentOwner(facts.session_id, facts.page,
                                 facts.room_id or prior.room_id)
        self._owners[slot_id] = facts
        return False


def page_identity(normalized_page: str) -> str:
    """Compare accepted public pages with creator casing ignored."""
    # The accepted host and /live suffix are fixed; only creator spelling varies.
    return normalized_page.lower()


def same_page(value: object, candidate: str) -> bool:
    """Compare an existing possibly mixed-case page with a canonical identity."""
    try:
        return page_identity(normalize_live_url(value)) == candidate
    except (TypeError, ValueError):
        return False


def same_room(value: object, candidate: str) -> bool:
    """Compare a proven room with a canonical expected room."""
    try:
        return canonical_room_id(value) == candidate
    except (TypeError, ValueError):
        return False


def _snapshot(controller: object) -> dict | None:
    getter = getattr(controller, "ownership", None)
    if not callable(getter):
        return None
    try:
        value = getter()
    except Exception:
        return None
    return value if isinstance(value, dict) else None


def _facts(value: dict) -> CurrentOwner | None:
    if not all(key in value for key in ("session_id", "source_url", "room_id")):
        return None
    session_id = value["session_id"]
    try:
        if type(session_id) is not str or str(UUID(session_id)) != session_id:
            return None
        page = page_identity(normalize_live_url(value["source_url"]))
        room = value["room_id"]
        room = None if room is None else canonical_room_id(room)
    except (TypeError, ValueError, AttributeError):
        return None
    return CurrentOwner(session_id, page, room)
