"""Discover a public TikTok room identity without depending on service state."""

from __future__ import annotations

import html
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any


# These public page templates embed JSON; arbitrary scripts are not identity sources.
_SCRIPT_PATTERN = re.compile(
    r"<script\b[^>]*\bid=[\"'](?:SIGI_STATE|__NEXT_DATA__)[\"'][^>]*>(.*?)</script>",
    re.IGNORECASE | re.DOTALL,
)
_ROOM_ID_PATTERN = re.compile(
    r'''["'](?:roomId|room_id)["']\s*:\s*(?:"([^"]*)"|'([^']*)'|([^,\s}\]<]+))'''
)
_DEEPLINK_ROOM_ID_PATTERN = re.compile(r'''snssdk\d*://live\?room_id=([^&"'\s<>]+)''')


def canonical_room_id(value: object) -> str:
    """Normalize a positive ASCII decimal room ID without limiting its width."""
    if type(value) is int:
        value = str(value)
    if not isinstance(value, str) or re.fullmatch(r"[0-9]+", value) is None:
        raise ValueError("invalid public room identity")
    # Remove representation-only zero padding; zero itself cannot anchor a LIVE.
    canonical = value.lstrip("0")
    if not canonical:
        raise ValueError("invalid public room identity")
    return canonical


@dataclass(frozen=True, slots=True)
class LiveResolution:
    """One resolved live room; transport fields are internal and excluded from repr.

    Use safe_diagnostics for logs/status, never generic dataclass serialization:
    asdict still includes the signed URL needed internally by the source layer.
    Offline and resolution failures are represented by the resolver's exceptions.
    """

    room_id: str
    flv_url: str = field(repr=False, compare=False)
    room_status: Any = field(default=2, repr=False, compare=False)
    rendition_label: str | None = field(default=None, repr=False, compare=False)
    rendition_source: str | None = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        # Frozen results carry canonical IDs even when constructed directly by tests/callers.
        object.__setattr__(self, "room_id", canonical_room_id(self.room_id))
        if type(self.room_status) not in {int, str} or str(self.room_status) != "2":
            raise ValueError("resolution requires a live room status")

    def safe_diagnostics(self) -> dict[str, str | bool]:
        """Expose proven public room identity without ephemeral transport metadata."""
        return {"room_id": self.room_id, "live": True}


def same_live(saved_room_id: object, resolution: LiveResolution | None) -> bool:
    """Compare room IDs only; missing/unprovable identity conservatively fails."""
    if not isinstance(resolution, LiveResolution):
        return False
    try:
        return canonical_room_id(saved_room_id) == resolution.room_id
    except ValueError:
        return False


def verify_room_identity(room: Mapping, requested_room_id: str) -> None:
    """Reject explicit room-info IDs that disagree with the public queried room."""
    requested_room_id = canonical_room_id(requested_room_id)
    for key in ("id", "id_str", "roomId", "room_id"):
        if key in room and canonical_room_id(room[key]) != requested_room_id:
            # Inspect only the room object: nested owners' user IDs are account identities.
            raise ValueError("conflicting public room identity")


def room_id_from_page(page: bytes) -> str | None:
    """Discover room identity in public page state or its embedded room links."""
    try:
        # HTML entities can escape quotes around embedded public room-state fields.
        text = html.unescape(page.decode("utf-8"))
    except UnicodeDecodeError as error:
        raise ValueError("public TikTok page is not valid UTF-8") from error
    identities = set()
    for script in _SCRIPT_PATTERN.findall(text):
        try:
            room_id = find_room_id(json.loads(script, object_pairs_hook=_unique_object))
        except json.JSONDecodeError:
            continue
        if room_id is not None:
            identities.add(room_id)
    if not identities:
        # Match whole values so a malformed ID such as 123bad cannot become room 123.
        for match in _ROOM_ID_PATTERN.finditer(text):
            raw = next(value for value in match.groups() if value is not None)
            identities.add(canonical_room_id(raw))
        for match in _DEEPLINK_ROOM_ID_PATTERN.finditer(text):
            identities.add(canonical_room_id(match.group(1)))
    return _one_identity(identities)


def find_room_id(value: Any) -> str | None:
    """Find one unambiguous roomId/room_id across nested public state."""
    return _one_identity(_room_ids(value))


def _room_ids(value: Any) -> set[str]:
    identities = set()
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key).replace("_", "").lower() == "roomid":
                identities.add(canonical_room_id(child))
            else:
                # Collect every identity rather than trusting traversal order in stale state.
                identities.update(_room_ids(child))
    elif isinstance(value, list):
        for child in value:
            identities.update(_room_ids(child))
    return identities


def _one_identity(identities: set[str]) -> str | None:
    if len(identities) > 1:
        raise ValueError("conflicting public room identity")
    return next(iter(identities), None)


def _unique_object(pairs: list[tuple[str, Any]]) -> dict:
    values = {}
    for name, value in pairs:
        # JSON's normal last-value-wins behavior can conceal conflicting room identity.
        if name in values:
            raise ValueError("ambiguous public response fields")
        values[name] = value
    return values
