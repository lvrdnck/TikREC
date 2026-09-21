"""Resolve an established TikTok LIVE from its retained canonical room identity."""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
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
    """Refresh an established room while proving its current account identity."""
    username = _validate_live_page_url(url)
    bound_room_id = canonical_room_id(room_id)
    if timeout <= 0:
        raise ValueError("timeout must be positive")

    direct, current_room_id = _resolve_known_room_and_account(
        username, bound_room_id, opener=opener, timeout=timeout
    )
    if direct is not None and current_room_id == bound_room_id:
        return direct

    try:
        result = _resolve_full_bound(
            url, username, bound_room_id, opener=opener, timeout=timeout
        )
    except TikTokOfflineError as error:
        if error.room_id != bound_room_id:
            # Only the saved room's numeric status may enter end confirmation.
            raise TikTokResolutionError(
                "different current public LIVE identity is not verifiably live"
            ) from error
        raise
    if (current_room_id is not None and current_room_id != bound_room_id
            and result.room_id != current_room_id):
        # Never let stale page state override a current conflicting account identity.
        raise TikTokResolutionError("conflicting current public LIVE identity")
    return result


def _resolve_known_room_and_account(username, room_id, *, opener, timeout):
    """Run independent saved-room and current-account requests concurrently."""
    with ThreadPoolExecutor(max_workers=2, thread_name_prefix="tikrec-resolver") as executor:
        room_future = executor.submit(
            _resolve_room, room_id, opener=opener, timeout=timeout
        )
        account_future = executor.submit(
            _room_id_from_public_lookup, username, opener=opener, timeout=timeout
        )
        direct = _resolution_or_none(room_future)
        current_room_id = _resolution_or_none(account_future)
    return direct, current_room_id


def _resolution_or_none(future):
    try:
        return future.result()
    except TikTokResolutionError:
        # The unchanged full bound path owns every insufficient fast-path result.
        return None


def _resolve_full_bound(url, username, room_id, *, opener, timeout):
    """Run the pre-fast-path established resolver as the conservative fallback."""
    try:
        return resolve_live(url, opener=opener, timeout=timeout)
    except TikTokResolutionError as error:
        if not _caused_by_http_404(error):
            raise
    return _resolve_without_live_page(
        username, room_id, opener=opener, timeout=timeout
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
    bound_live = None
    bound_offline = None
    bound_failure = None
    try:
        bound_live = _resolve_room(room_id, opener=opener, timeout=timeout)
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
        if bound_live is not None:
            # A live saved room cannot prove that the username still owns it.
            raise lookup_error
        if bound_offline is not None:
            raise bound_offline
        raise bound_failure from lookup_error

    if current_room_id != room_id:
        try:
            return _resolve_room(current_room_id, opener=opener, timeout=timeout)
        except TikTokResolutionError as current_error:
            if bound_offline is not None:
                raise bound_offline
            if bound_failure is not None:
                raise bound_failure from current_error
            # The saved room is live, so another room's failure is not offline evidence.
            raise TikTokResolutionError(
                "different current public LIVE identity is not verifiably live"
            ) from current_error
    if bound_live is not None:
        return bound_live
    if bound_offline is not None:
        raise bound_offline
    raise bound_failure


def _caused_by_http_404(error):
    cause = error.__cause__
    return isinstance(cause, HTTPError) and cause.code == 404
