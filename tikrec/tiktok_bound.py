"""Resolve an established TikTok LIVE from its retained canonical room identity."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from urllib.error import HTTPError
from urllib.request import urlopen

from .tiktok import (
    TikTokOfflineError,
    TikTokResolutionError,
    _ResolvedLiveUrl,
    _resolve_room,
    _room_id_from_public_lookup,
    _validate_live_page_url,
    resolve_live,
)
from .tiktok_identity import LiveResolution, canonical_room_id


def resolve_live_bound(
    url: str,
    room_id: str,
    *,
    opener: Callable[..., Any] = urlopen,
    timeout: float = 15,
) -> LiveResolution:
    """Resolve an established room when its account LIVE page returns HTTP 404."""
    username = _validate_live_page_url(url)
    bound_room_id = canonical_room_id(room_id)
    try:
        return resolve_live(url, opener=opener, timeout=timeout)
    except TikTokResolutionError as error:
        if not _caused_by_http_404(error):
            raise
    return _resolve_without_live_page(
        username, bound_room_id, opener=opener, timeout=timeout
    )


def resolve_live_url_bound(
    url: str,
    room_id: str,
    *,
    opener: Callable[..., Any] = urlopen,
    timeout: float = 15,
) -> str:
    """Return a string-compatible transport for an established public room."""
    result = resolve_live_bound(url, room_id, opener=opener, timeout=timeout)
    return _ResolvedLiveUrl(
        result.flv_url,
        result.room_status,
        result.rendition_label,
        result.rendition_source,
        result.room_id,
    )


def _resolve_without_live_page(username, room_id, *, opener, timeout):
    bound_offline = None
    bound_failure = None
    try:
        return _resolve_room(room_id, opener=opener, timeout=timeout)
    except TikTokOfflineError as error:
        # Preserve trustworthy prior-room status while checking for a newer identity.
        bound_offline = error
    except TikTokResolutionError as error:
        bound_failure = error

    try:
        current_room_id = _room_id_from_public_lookup(
            username, opener=opener, timeout=timeout
        )
    except TikTokResolutionError as lookup_error:
        if bound_offline is not None:
            raise bound_offline
        raise bound_failure from lookup_error

    if current_room_id != room_id:
        try:
            return _resolve_room(current_room_id, opener=opener, timeout=timeout)
        except TikTokResolutionError as current_error:
            if bound_offline is not None:
                raise bound_offline
            raise bound_failure from current_error
    if bound_offline is not None:
        raise bound_offline
    raise bound_failure


def _caused_by_http_404(error):
    cause = error.__cause__
    return isinstance(cause, HTTPError) and cause.code == 404
