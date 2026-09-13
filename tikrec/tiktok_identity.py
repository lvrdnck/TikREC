"""Discover a public TikTok room identity without depending on service state."""

from __future__ import annotations

import html
import json
import re
from collections.abc import Mapping
from typing import Any


_SCRIPT_PATTERN = re.compile(
    r"<script\b[^>]*\bid=[\"'](?:SIGI_STATE|__NEXT_DATA__)[\"'][^>]*>(.*?)</script>",
    re.IGNORECASE | re.DOTALL,
)
_ROOM_ID_PATTERN = re.compile(r'["\'](?:roomId|room_id)["\']\s*:\s*["\']?(\d+)')
_DEEPLINK_ROOM_ID_PATTERN = re.compile(r"snssdk\d*://live\?room_id=(\d+)")


def room_id_from_page(page: bytes) -> str | None:
    """Discover room identity in public page state or its embedded room links."""
    try:
        text = html.unescape(page.decode("utf-8"))
    except UnicodeDecodeError as error:
        raise ValueError("public TikTok page is not valid UTF-8") from error
    for script in _SCRIPT_PATTERN.findall(text):
        try:
            room_id = find_room_id(json.loads(script))
        except json.JSONDecodeError:
            continue
        if room_id is not None:
            return room_id
    match = _ROOM_ID_PATTERN.search(text) or _DEEPLINK_ROOM_ID_PATTERN.search(text)
    if match:
        return match.group(1)
    return None


def find_room_id(value: Any) -> str | None:
    """Find a roomId/room_id field in nested public page or lookup state."""
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key).replace("_", "").lower() == "roomid" and str(child).isdigit():
                return str(child)
            room_id = find_room_id(child)
            if room_id is not None:
                return room_id
    elif isinstance(value, list):
        for child in value:
            room_id = find_room_id(child)
            if room_id is not None:
                return room_id
    return None
