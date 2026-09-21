"""Established-room resolution keeps identity safety on its fast path."""

import json
from collections import deque
from threading import Barrier, Lock
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit

import pytest

from tests.test_tiktok import _Opener, _Response, live_page, live_room
from tikrec.tiktok import (TikTokOfflineError, TikTokResolutionError,
                           TikTokResolutionTransientError, resolve_live)
from tikrec.tiktok_bound import resolve_live_bound


PAGE = "https://www.tiktok.com/@creator/live"
SIGNED = "https://cdn.test/live.flv?signature=secret"


def page_404():
    return HTTPError(PAGE, 404, "missing", {}, None)


def public_room(room_id):
    return json.dumps({"statusCode": 0, "data": {"roomId": room_id}}).encode()


def room_info(room_id="123", *, status=2, label="HD1", url=SIGNED):
    body = json.loads(live_room({label: url} if status == 2 else {}, status=status))
    body["data"]["room_id"] = room_id
    return json.dumps(body).encode()


class _RouteOpener:
    """Serve URL-specific queues so concurrent request order is irrelevant."""

    def __init__(self, routes, *, synchronize_fast=False):
        self.routes = {key: deque(values) for key, values in routes.items()}
        self.urls = []
        self._lock = Lock()
        self._barrier = Barrier(2) if synchronize_fast else None

    def __call__(self, request, **_):
        key = self._key(request.full_url)
        with self._lock:
            self.urls.append(request.full_url)
            response = self.routes[key].popleft()
        if self._barrier is not None and key in {"account", "room:123"}:
            self._barrier.wait(timeout=2)
        return _Response(response)

    @staticmethod
    def _key(url):
        parsed = urlsplit(url)
        if url == PAGE:
            return "page"
        if parsed.path == "/api-live/user/room/":
            return "account"
        if parsed.path == "/webcast/room/info/":
            return "room:" + parse_qs(parsed.query)["room_id"][0]
        raise AssertionError("unexpected public resolver request")


def test_initial_page_404_remains_resolution_failure_without_room_invention():
    opener = _Opener([page_404()])
    with pytest.raises(TikTokResolutionError) as failure:
        resolve_live(PAGE, opener=opener)
    assert not isinstance(failure.value, TikTokOfflineError)
    assert opener.urls == [PAGE]


def test_saved_room_live_and_current_account_same_use_parallel_fast_path():
    opener = _RouteOpener({
        "room:123": [room_info(url=SIGNED + "&fresh=1")],
        "account": [public_room("123")],
    }, synchronize_fast=True)

    result = resolve_live_bound(PAGE, "123", opener=opener)

    assert result.room_id == "123" and result.flv_url.endswith("&fresh=1")
    assert result.safe_diagnostics() == {"room_id": "123", "live": True}
    assert "cdn.test" not in repr(result) and "signature" not in repr(result)
    assert PAGE not in opener.urls and len(opener.urls) == 2


def test_bound_page_404_retries_same_room_with_current_account_evidence():
    opener = _RouteOpener({
        "room:123": [b"not json", room_info()],
        "account": [b'{"statusCode":0,"data":{}}', public_room("123")],
        "page": [page_404()],
    })

    result = resolve_live_bound(PAGE, "123", opener=opener)

    assert result.room_id == "123" and result.flv_url == SIGNED
    assert PAGE in opener.urls


def test_bound_page_404_uses_trustworthy_prior_room_offline_evidence():
    opener = _RouteOpener({
        "room:123": [room_info(status=4), room_info(status=4)],
        "account": [public_room("123"), public_room("123")],
        "page": [page_404()],
    })
    with pytest.raises(TikTokOfflineError) as failure:
        resolve_live_bound(PAGE, "123", opener=opener)
    assert failure.value.room_id == "123" and failure.value.status == 4


def test_bound_page_404_exposes_a_different_current_live_identity():
    opener = _RouteOpener({
        "room:123": [room_info(), room_info()],
        "room:456": [room_info("456", url=SIGNED + "&room=456")],
        "account": [public_room("456"), public_room("456")],
        "page": [page_404()],
    })

    result = resolve_live_bound(PAGE, "123", opener=opener)

    assert result.room_id == "456"
    assert parse_qs(urlsplit(opener.urls[-1]).query)["room_id"] == ["456"]


def test_different_current_room_with_unverifiable_transport_fails_closed():
    opener = _RouteOpener({
        "room:123": [room_info(), room_info()],
        "room:456": [b"not json"],
        "account": [public_room("456"), public_room("456")],
        "page": [page_404()],
    })

    with pytest.raises(TikTokResolutionError) as failure:
        resolve_live_bound(PAGE, "123", opener=opener)
    assert type(failure.value) is TikTokResolutionError


def test_different_current_room_offline_is_not_saved_room_offline_evidence():
    opener = _RouteOpener({
        "room:123": [room_info(), room_info()],
        "room:456": [room_info("456", status=4)],
        "account": [public_room("456"), public_room("456")],
        "page": [page_404()],
    })

    with pytest.raises(TikTokResolutionError) as failure:
        resolve_live_bound(PAGE, "123", opener=opener)
    assert not isinstance(failure.value, TikTokOfflineError)


def test_bound_page_404_with_unverifiable_room_state_fails_closed():
    opener = _RouteOpener({
        "room:123": [b"not json", b"not json"],
        "account": [b'{"statusCode":0,"data":{}}'] * 2,
        "page": [page_404()],
    })
    with pytest.raises(TikTokResolutionError) as failure:
        resolve_live_bound(PAGE, "123", opener=opener)
    assert not isinstance(failure.value, TikTokOfflineError)


def test_malformed_direct_response_falls_back_to_full_bound_resolution():
    opener = _RouteOpener({
        "room:123": [b"not json", room_info(url=SIGNED + "&fallback=1")],
        "account": [public_room("123")],
        "page": [live_page("123")],
    })

    result = resolve_live_bound(PAGE, "123", opener=opener)

    assert result.flv_url.endswith("&fallback=1") and PAGE in opener.urls


def test_malformed_account_response_never_accepts_unverified_fast_transport():
    opener = _RouteOpener({
        "room:123": [room_info(url=SIGNED + "&fast=1"),
                     room_info(url=SIGNED + "&fallback=1")],
        "account": [b'{"statusCode":0,"data":{}}'],
        "page": [live_page("123")],
    })

    result = resolve_live_bound(PAGE, "123", opener=opener)

    assert result.flv_url.endswith("&fallback=1") and PAGE in opener.urls


def test_account_transient_failure_and_page_404_fail_closed_without_fast_acceptance():
    transient = HTTPError(PAGE, 503, "busy", {}, None)
    opener = _RouteOpener({
        "room:123": [room_info()] * 2,
        "account": [transient, transient],
        "page": [page_404()],
    })

    with pytest.raises(TikTokResolutionTransientError):
        resolve_live_bound(PAGE, "123", opener=opener)


def test_direct_transient_failure_retains_full_bound_recovery_semantics():
    transient = HTTPError(PAGE, 503, "busy", {}, None)
    opener = _RouteOpener({
        "room:123": [transient],
        "account": [public_room("123")],
        "page": [transient],
    })

    with pytest.raises(TikTokResolutionTransientError):
        resolve_live_bound(PAGE, "123", opener=opener)


def test_explicit_conflicting_direct_identity_is_rejected_then_safely_falls_back():
    opener = _RouteOpener({
        "room:123": [room_info("456"), room_info(url=SIGNED + "&fallback=1")],
        "account": [public_room("123")],
        "page": [live_page("123")],
    })

    result = resolve_live_bound(PAGE, "123", opener=opener)

    assert result.room_id == "123" and result.flv_url.endswith("&fallback=1")


def test_stale_page_cannot_override_conflicting_current_account_identity():
    opener = _RouteOpener({
        "room:123": [room_info(), room_info()],
        "account": [public_room("456")],
        "page": [live_page("123")],
    })

    with pytest.raises(TikTokResolutionError, match="conflicting current") as failure:
        resolve_live_bound(PAGE, "123", opener=opener)
    assert "signature" not in str(failure.value)
