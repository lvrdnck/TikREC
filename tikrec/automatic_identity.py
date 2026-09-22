"""Bind an unattended capture's resolver calls to one observed public room."""

from __future__ import annotations

from collections.abc import Callable

from .tiktok import TikTokResolutionError, resolve_live_url
from .tiktok_bound import resolve_live_url_bound
from .tiktok_identity import canonical_room_id


def expected_room_resolvers(
    expected_room_id: str,
    *,
    resolver: Callable[[str], object] = resolve_live_url,
    bound_resolver: Callable[[str, str], object] = resolve_live_url_bound,
) -> dict[str, Callable]:
    """Return initial and reconnect resolvers that require the observed room."""
    expected = canonical_room_id(expected_room_id)

    def verify(result: object) -> object:
        current = getattr(result, "room_id", None)
        try:
            current = canonical_room_id(current)
        except (TypeError, ValueError):
            raise TikTokResolutionError(
                "automatic start could not verify observed LIVE identity"
            ) from None
        if current != expected:
            raise TikTokResolutionError(
                "automatic start observed a different LIVE identity"
            )
        return result

    def initial(page: str) -> object:
        return verify(resolver(page))

    def established(page: str, room_id: str) -> object:
        return verify(bound_resolver(page, room_id))

    return {"resolver": initial, "bound_resolver": established}
