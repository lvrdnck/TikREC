"""Resolve public TikTok LIVE page URLs to direct FLV playback URLs."""

from __future__ import annotations

import json
import re
import time
from collections.abc import Callable, Mapping
from http.client import HTTPException
from typing import Any
from urllib.error import URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

from .tiktok_identity import (LiveResolution, find_room_id as _find_room_id,
                              room_id_from_page, same_live, verify_room_identity,
                              _unique_object)


_ROOM_INFO_URL = "https://webcast.tiktok.com/webcast/room/info/"
_PUBLIC_ROOM_URL = "https://www.tiktok.com/api-live/user/room/"
_USER_AGENT = "Mozilla/5.0 (compatible; TikREC/0.1)"


class TikTokResolutionError(RuntimeError):
    """Raised when a public TikTok LIVE URL cannot yield a direct FLV URL."""


class TikTokOfflineError(TikTokResolutionError):
    """Raised only after room-info confirms that a room is not live."""

    def __init__(self, message: str, status: Any = None, room_id: str | None = None) -> None:
        super().__init__(message)
        # Keep the JSON value unchanged so outage evidence distinguishes strings and numbers.
        self.status = status
        self.room_id = room_id


class TikTokResolutionTransientError(TikTokResolutionError):
    """Raised for a network failure that a live capture may retry."""


class _ResolvedLiveUrl(str):
    """A string-compatible URL carrying raw room status and the selected rendition."""

    def __new__(cls, url: str, status: Any, label: str | None = None,
                source: str | None = None, room_id: str | None = None) -> _ResolvedLiveUrl:
        value = super().__new__(cls, url)
        # A str subclass preserves the resolver's public contract for callers and CLI output.
        value.room_status = status
        value.rendition_label = label
        value.rendition_source = source
        value.room_id = room_id
        return value


def resolve_live_url(
    url: str,
    *,
    opener: Callable[..., Any] = urlopen,
    timeout: float = 15,
) -> str:
    """Resolve one public TikTok LIVE page URL to its current HTTPS FLV URL."""
    result = resolve_live(url, opener=opener, timeout=timeout)
    # Preserve the string URL and its existing observation attributes for legacy callers.
    return _ResolvedLiveUrl(result.flv_url, result.room_status, result.rendition_label,
                            result.rendition_source, result.room_id)


def resolve_live(
    url: str,
    *,
    opener: Callable[..., Any] = urlopen,
    timeout: float = 15,
) -> LiveResolution:
    """Resolve current public LIVE identity and transport; never wait for a future LIVE."""
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
    room = _live_room(room_info, room_id)
    renditions = _flv_renditions(room)
    if not renditions:
        raise TikTokResolutionError(
            "live room has no public HTTP(S) FLV rendition in flv_pull_url or "
            "rtmp_pull_url"
        )
    label, source_rank, selected_url = sorted(
        renditions,
        key=lambda item: (-_quality_score(item[0]), item[1], item[0], item[2]),
    )[0]
    # Carry the existing choice without persisting signed CDN URLs or changing ranking.
    return LiveResolution(room_id, selected_url, room.get("status"), label,
                          ("flv_pull_url", "rtmp_pull_url")[source_rank])


def resolve_live_url_confirmed(
    url: str,
    *,
    resolver: Callable[[str], str],
    capture_started: bool,
    checks: int = 3,
    interval: float = 5.0,
    sleeper: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.time,
    status_observer: Callable[[float, Any, bool], None] | None = None,
) -> str:
    """Resolve a URL, requiring spaced non-live results after capture has begun."""
    if not isinstance(checks, int) or checks < 1:
        raise ValueError("offline confirmation checks must be a positive integer")
    if interval < 0:
        raise ValueError("offline confirmation interval must not be negative")
    try:
        return resolver(url)
    except TikTokOfflineError as first_error:
        # Python clears exception-target names after ``except`` to break cycles.
        offline_error = first_error

    for attempt in range(checks):
        if attempt:
            sleeper(interval)
            try:
                direct_url = resolver(url)
            except TikTokOfflineError as next_error:
                offline_error = next_error
            else:
                if status_observer is not None:
                    # Injected resolvers return plain strings, whose successful status is 2.
                    status = getattr(direct_url, "room_status", 2)
                    status_observer(clock(), status, False)
                return direct_url
        confirmed = not capture_started or attempt + 1 == checks
        if status_observer is not None:
            status_observer(clock(), offline_error.status, confirmed)
        if confirmed:
            raise offline_error

    raise AssertionError("offline confirmation loop did not resolve or raise")


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
        # Transport diagnostics may contain signed URLs even though identity never uses them.
        raise TikTokResolutionTransientError(
            "TikTok network request failed: " + re.sub(r"https?://\S+", "[URL redacted]", str(error))
        ) from error


def _room_id_from_page(page: bytes) -> str | None:
    try:
        return room_id_from_page(page)
    except ValueError as error:
        # Keep the public resolver's exception contract after extracting page parsing.
        raise TikTokResolutionError(str(error)) from error


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
    try:
        room_id = _find_room_id(response.get("data"))
    except ValueError as error:
        raise TikTokResolutionError(str(error)) from error
    if room_id is None:
        raise TikTokResolutionError("unable to determine room ID from public TikTok response")
    return room_id


def _json_response(response: bytes, description: str) -> Mapping[str, Any]:
    try:
        value = json.loads(response, object_pairs_hook=_unique_object)
    except (UnicodeDecodeError, ValueError) as error:
        raise TikTokResolutionError(f"malformed {description} JSON response") from error
    if not isinstance(value, Mapping):
        raise TikTokResolutionError(f"malformed {description} response")
    return value


def _live_room(response: Mapping[str, Any], room_id: str) -> Mapping[str, Any]:
    status_code = response.get("status_code", response.get("statusCode", 0))
    if not _numeric_status(status_code):
        raise TikTokResolutionError("malformed room-info status code")
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
    if "room" in data and not isinstance(room, Mapping):
        raise TikTokResolutionError("malformed room-info room data")
    room = room if isinstance(room, Mapping) else data
    try:
        verify_room_identity(room, room_id)
    except ValueError as error:
        raise TikTokResolutionError(str(error)) from error
    room_status = room.get("status")
    if not _numeric_status(room_status):
        # Missing or nonnumeric status is malformed evidence, not confirmation of offline.
        raise TikTokResolutionError("malformed room-info room status")
    if str(room_status) != "2":
        raise TikTokOfflineError("TikTok account or room is not live", room_status, room_id)
    return room


def _numeric_status(value: Any) -> bool:
    # JSON booleans and missing/container values cannot establish room end evidence.
    return ((type(value) is int and value >= 0) or
            (type(value) is str and re.fullmatch(r"[0-9]+", value) is not None))


def _flv_renditions(room: Mapping[str, Any]) -> list[tuple[str, int, str]]:
    stream_url = room.get("stream_url")
    if not isinstance(stream_url, Mapping):
        raise TikTokResolutionError("malformed room-info stream URL data")
    renditions: list[tuple[str, int, str]] = []
    for source_rank, field in enumerate(("flv_pull_url", "rtmp_pull_url")):
        values = stream_url.get(field)
        if isinstance(values, str):
            values = {"default": values}
        if not isinstance(values, Mapping):
            continue
        # TikTok sometimes publishes HTTPS FLV only in the misleading rtmp field.
        # The source rank retains flv_pull_url as the deterministic tie-breaker.
        renditions.extend(
            (str(name).lower(), source_rank, value)
            for name, value in values.items()
            if isinstance(value, str) and _is_http_flv_url(value)
        )
    return renditions


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
