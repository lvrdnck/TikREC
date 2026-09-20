"""Established-room resolution stays safe when the username LIVE page disappears."""

import json
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit

import pytest

from tests.test_tiktok import _Opener, live_room
from tikrec.tiktok import (TikTokOfflineError, TikTokResolutionError,
                           resolve_live)
from tikrec.tiktok_bound import resolve_live_bound


PAGE = "https://www.tiktok.com/@creator/live"
SIGNED = "https://cdn.test/live.flv?signature=secret"


def page_404():
    return HTTPError(PAGE, 404, "missing", {}, None)


def public_room(room_id):
    return json.dumps({"statusCode": 0, "data": {"roomId": room_id}}).encode()


def test_initial_page_404_remains_resolution_failure_without_room_invention():
    opener = _Opener([page_404()])
    with pytest.raises(TikTokResolutionError) as failure:
        resolve_live(PAGE, opener=opener)
    assert not isinstance(failure.value, TikTokOfflineError)
    assert opener.urls == [PAGE]


def test_bound_page_404_uses_same_room_live_evidence():
    opener = _Opener([page_404(), live_room({"HD1": SIGNED})])
    result = resolve_live_bound(PAGE, "123", opener=opener)
    assert result.room_id == "123" and result.flv_url == SIGNED
    assert parse_qs(urlsplit(opener.urls[-1]).query)["room_id"] == ["123"]


def test_bound_page_404_uses_trustworthy_prior_room_offline_evidence():
    opener = _Opener([page_404(), live_room({}, status=4), public_room("123")])
    with pytest.raises(TikTokOfflineError) as failure:
        resolve_live_bound(PAGE, "123", opener=opener)
    assert failure.value.room_id == "123" and failure.value.status == 4


def test_bound_page_404_exposes_a_different_current_live_identity():
    opener = _Opener([
        page_404(), live_room({}, status=4), public_room("456"),
        live_room({"HD1": SIGNED}),
    ])
    result = resolve_live_bound(PAGE, "123", opener=opener)
    assert result.room_id == "456"
    assert parse_qs(urlsplit(opener.urls[-1]).query)["room_id"] == ["456"]


def test_bound_page_404_with_unverifiable_room_state_fails_closed():
    opener = _Opener([page_404(), b"not json", b'{"statusCode":0,"data":{}}'])
    with pytest.raises(TikTokResolutionError) as failure:
        resolve_live_bound(PAGE, "123", opener=opener)
    assert not isinstance(failure.value, TikTokOfflineError)
