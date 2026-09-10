"""Resolve public TikTok LIVE page URLs to direct FLV playback URLs."""

from __future__ import annotations

import html
import json
import re
from collections.abc import Callable, Mapping
from http.client import HTTPException
from typing import Any
from urllib.error import URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen


_ROOM_INFO_URL = "https://webcast.tiktok.com/webcast/room/info/"
_PUBLIC_ROOM_URL = "https://www.tiktok.com/api-live/user/room/"
_USER_AGENT = "Mozilla/5.0 (compatible; TikREC/0.1)"
_SCRIPT_PATTERN = re.compile(
    r"<script\b[^>]*\bid=[\"'](?:SIGI_STATE|__NEXT_DATA__)[\"'][^>]*>(.*?)</script>",
    re.IGNORECASE | re.DOTALL,
)
_ROOM_ID_PATTERN = re.compile(r'["\'](?:roomId|room_id)["\']\s*:\s*["\']?(\d+)')
_DEEPLINK_ROOM_ID_PATTERN = re.compile(r"snssdk\d*://live\?room_id=(\d+)")


class TikTokResolutionError(RuntimeError):
    """Raised when a public TikTok LIVE URL cannot yield a direct FLV URL."""


class TikTokOfflineError(TikTokResolutionError):
    """Raised only after room-info confirms that a room is not live."""


class TikTokResolutionTransientError(TikTokResolutionError):
    """Raised for a network failure that a live capture may retry."""


def resolve_live_url(
    url: str,
    *,
    opener: Callable[..., Any] = urlopen,
    timeout: float = 15,
) -> str:
    """Resolve one public TikTok LIVE page URL to its current HTTPS FLV URL."""
    username = _validate_live_page_url(url)
    if timeout <= 0:
        raise ValueError("timeout must be positive")
    room_id = _room_id_from_page(_read_public_url(url, opener=opener, timeout=timeout))
    if room_id is None:
        room_id = _room_id_from_public_lookup(username, opener=opener, timeout=timeout)
    room_info_url = f"{_ROOM_INFO_URL}?{urlencode({'aid': 1988, 'room_id': room_id})}"
    room_info = _json_response(
        _read_public_url(room_info_url, opener=opener, timeout=timeout),
        "room-info",
    )
    room = _live_room(room_info)
    renditions = _flv_renditions(room)
    if not renditions:
        raise TikTokResolutionError("live room has no public FLV rendition")
    return sorted(renditions, key=lambda item: (-_quality_score(item[0]), item[0], item[1]))[0][1]


def _validate_live_page_url(url: str) -> str:
    parsed = urlsplit(url)
    host = parsed.hostname.lower() if parsed.hostname else ""
    path = [segment for segment in parsed.path.split("/") if segment]
    if (
        parsed.scheme not in {"http", "https"}
        or not (host == "tiktok.com" or host.endswith(".tiktok.com"))
        or len(path) < 2
        or not path[0].startswith("@")
        or len(path[0]) == 1
        or path[1].lower() != "live"
    ):
        raise TikTokResolutionError("unsupported or malformed public TikTok LIVE URL")
    return path[0][1:]


def _read_public_url(
    url: str, *, opener: Callable[..., Any], timeout: float
) -> bytes:
    request = Request(url, headers={"User-Agent": _USER_AGENT})
    try:
        with opener(request, timeout=timeout) as response:
            return response.read()
    # Short or malformed HTTP bodies raise HTTPException during ``read()``,
    # after a connection has opened but before a usable TikTok response exists.
    except (HTTPException, OSError, URLError) as error:
        raise TikTokResolutionTransientError(
            f"TikTok network request failed: {error}"
        ) from error


def _room_id_from_page(page: bytes) -> str | None:
    try:
        text = html.unescape(page.decode("utf-8"))
    except UnicodeDecodeError as error:
        raise TikTokResolutionError("public TikTok page is not valid UTF-8") from error
    for script in _SCRIPT_PATTERN.findall(text):
        try:
            room_id = _find_room_id(json.loads(script))
        except json.JSONDecodeError:
            continue
        if room_id is not None:
            return room_id
    match = _ROOM_ID_PATTERN.search(text) or _DEEPLINK_ROOM_ID_PATTERN.search(text)
    if match:
        return match.group(1)
    return None


def _room_id_from_public_lookup(
    username: str, *, opener: Callable[..., Any], timeout: float
) -> str:
    query = urlencode({"aid": 1988, "uniqueId": username, "sourceType": 54})
    response = _json_response(
        _read_public_url(f"{_PUBLIC_ROOM_URL}?{query}", opener=opener, timeout=timeout),
        "public room lookup",
    )
    if str(response.get("statusCode", response.get("status_code", 0))) != "0":
        raise TikTokResolutionError("unable to determine room ID from public TikTok response")
    room_id = _find_room_id(response.get("data"))
    if room_id is None:
        raise TikTokResolutionError("unable to determine room ID from public TikTok response")
    return room_id


def _find_room_id(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key).replace("_", "").lower() == "roomid" and str(child).isdigit():
                return str(child)
            room_id = _find_room_id(child)
            if room_id is not None:
                return room_id
    elif isinstance(value, list):
        for child in value:
            room_id = _find_room_id(child)
            if room_id is not None:
                return room_id
    return None


def _json_response(response: bytes, description: str) -> Mapping[str, Any]:
    try:
        value = json.loads(response)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise TikTokResolutionError(f"malformed {description} JSON response") from error
    if not isinstance(value, Mapping):
        raise TikTokResolutionError(f"malformed {description} response")
    return value


def _live_room(response: Mapping[str, Any]) -> Mapping[str, Any]:
    status_code = response.get("status_code", response.get("statusCode", 0))
    if str(status_code) == "4003110":
        raise TikTokResolutionError(
            "this room's stream is not available to anonymous requests -- "
            "TikREC only records publicly accessible streams "
            f"(TikTok status code {status_code})"
        )
    if str(status_code) != "0":
        raise TikTokResolutionError(f"room-info returned TikTok status code {status_code}")
    data = response.get("data")
    if not isinstance(data, Mapping):
        raise TikTokResolutionError("malformed room-info response data")
    room = data.get("room")
    room = room if isinstance(room, Mapping) else data
    if str(room.get("status")) != "2":
        raise TikTokOfflineError("TikTok account or room is not live")
    return room


def _flv_renditions(room: Mapping[str, Any]) -> list[tuple[str, str]]:
    stream_url = room.get("stream_url")
    if not isinstance(stream_url, Mapping):
        raise TikTokResolutionError("malformed room-info stream URL data")
    values = stream_url.get("flv_pull_url")
    if isinstance(values, str):
        values = {"default": values}
    if not isinstance(values, Mapping):
        return []
    return [
        (str(name).lower(), value)
        for name, value in values.items()
        if isinstance(value, str) and _is_http_flv_url(value)
    ]


def _is_http_flv_url(url: str) -> bool:
    parsed = urlsplit(url)
    return parsed.scheme in {"http", "https"} and parsed.path.lower().endswith(".flv")


def _quality_score(name: str) -> int:
    normalized = name.lower()
    if any(marker in normalized for marker in ("origin", "origion", "full_hd", "1080", "uhd")):
        return 3
    if "hd" in normalized or "720" in normalized:
        return 2
    if "sd" in normalized:
        return 1
    return 0
