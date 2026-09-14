"""Offline checks for public room identity discovery and safe comparisons."""

import json
import socket
from dataclasses import FrozenInstanceError, replace
from urllib.error import HTTPError, URLError

import pytest

from tests.test_tiktok import _Opener, live_page, live_room
from tikrec.tiktok import (TikTokOfflineError, TikTokResolutionError,
                           TikTokResolutionTransientError, resolve_live, resolve_live_url)
from tikrec.tiktok_identity import (LiveResolution, canonical_room_id, find_room_id,
                                    room_id_from_page, same_live)


PAGE = "https://www.tiktok.com/@creator/live"
SIGNED = "https://cdn.test/live.flv?signature=secret"


def test_finds_nested_public_room_id():
    assert find_room_id({"data": [{"roomId": 123456}]}) == "123456"


def test_page_without_identity_returns_none():
    assert room_id_from_page(b"<html>no public state</html>") is None


def test_page_state_preserves_room_id():
    assert room_id_from_page(b'<script id="SIGI_STATE">{"roomId":"456"}</script>') == "456"


def test_invalid_page_encoding_fails():
    with pytest.raises(ValueError, match="not valid UTF-8"):
        room_id_from_page(b"\xff")


def resolve(room_id="123456", room=None):
    return resolve_live(PAGE, opener=_Opener([
        live_page(room_id), live_room({"HD1": SIGNED}) if room is None else room,
    ]))


def test_structured_resolution_exposes_identity_and_internal_transport():
    result = resolve("987654")
    assert isinstance(result, LiveResolution)
    assert result.room_id == "987654" and result.flv_url == SIGNED
    assert result.room_status == 2
    assert (result.rendition_label, result.rendition_source) == ("hd1", "flv_pull_url")
    with pytest.raises(FrozenInstanceError):
        result.room_id = "changed"


def test_legacy_url_wrapper_preserves_string_and_observation_contract():
    result = resolve_live_url(PAGE, opener=_Opener([live_page(), live_room({"HD1": SIGNED}, "2")]))
    assert isinstance(result, str) and str(result) == SIGNED
    assert result.room_id == "123456" and result.room_status == "2"
    assert (result.rendition_label, result.rendition_source) == ("hd1", "flv_pull_url")


def test_structured_resolution_from_public_lookup():
    lookup = json.dumps({"statusCode": 0, "data": {"liveRoom": {"roomId": 987654}}}).encode()
    result = resolve_live(PAGE, opener=_Opener([b"<html></html>", lookup, live_room({"HD1": SIGNED})]))
    assert result.room_id == "987654"


@pytest.mark.parametrize("raw,expected", [(123, "123"), ("123", "123"),
    ("000123", "123"), ("184467440737095516160", "184467440737095516160")])
def test_canonical_id_is_positive_ascii_decimal_string(raw, expected):
    assert canonical_room_id(raw) == expected
    assert resolve(raw).room_id == expected


@pytest.mark.parametrize("raw", [None, "", " ", " 123", "123 ", "12x", "1.5",
    "123e4", "0", 0, -1, "-1", "+1", True, False, 123.0, "１２３", {}, []])
def test_malformed_identity_is_rejected_without_reflecting_values(raw):
    with pytest.raises(ValueError, match="invalid public room identity"):
        canonical_room_id(raw)
    with pytest.raises(TikTokResolutionError) as failure:
        resolve(raw)
    assert not isinstance(failure.value, TikTokOfflineError)


@pytest.mark.parametrize("page", [
    b'<script id="SIGI_STATE">{"roomId":"123","nested":{"room_id":"456"}}</script>',
    b'<script id="SIGI_STATE">{"roomId":"123"}</script><script id="__NEXT_DATA__">{"roomId":"456"}</script>',
    b'{"roomId":"123"} {"room_id":"456"}',
    b'<script id="SIGI_STATE">{"roomId":"123","roomId":"456"}</script>',
])
def test_ambiguous_page_identity_fails(page):
    with pytest.raises(TikTokResolutionError):
        resolve_live(PAGE, opener=_Opener([page]))


def test_repeated_equivalent_ids_are_not_ambiguous():
    assert find_room_id({"roomId": "00123", "nested": {"room_id": 123}}) == "123"


@pytest.mark.parametrize("page", [b'{"roomId":"123bad"}', b'{"roomId":""}',
                                 b'{"roomId":123.5}', b'{"roomId":123e4}'])
def test_raw_page_regex_never_accepts_a_numeric_prefix(page):
    with pytest.raises(TikTokResolutionError):
        resolve_live(PAGE, opener=_Opener([page]))


def test_ambiguous_public_lookup_fails():
    lookup = b'{"statusCode":0,"data":{"roomId":"123","room_id":"456"}}'
    with pytest.raises(TikTokResolutionError):
        resolve_live(PAGE, opener=_Opener([b"<html></html>", lookup]))


@pytest.mark.parametrize("field", ["id", "id_str", "roomId", "room_id"])
def test_room_info_identity_must_agree_with_requested_room(field):
    room = json.loads(live_room({"HD1": SIGNED}))
    room["data"][field] = "456"
    with pytest.raises(TikTokResolutionError, match="conflicting public room identity"):
        resolve("123", json.dumps(room).encode())


def test_matching_room_info_id_preserves_large_numeric_identity():
    room = json.loads(live_room({"HD1": SIGNED}))
    room["data"]["id"] = 184467440737095516160
    assert resolve("184467440737095516160", json.dumps(room).encode()).room_id == "184467440737095516160"


def test_same_live_uses_only_public_room_id():
    result = resolve("123")
    assert same_live("123", result)
    assert same_live("00123", result)
    assert not same_live("456", result)
    assert same_live("123", replace(result, flv_url="https://other.test/different.flv?secret=x"))
    assert not same_live("456", replace(result, flv_url=SIGNED))


@pytest.mark.parametrize("saved", [None, "", PAGE, "creator", SIGNED, "0", "１２３", {}])
def test_unprovable_saved_identity_never_matches(saved):
    assert not same_live(saved, resolve("123"))


def test_missing_current_resolution_cannot_match():
    assert not same_live("123", None)
    assert not same_live("123", SIGNED)


@pytest.mark.parametrize("status", [4, "4", 3, 0])
def test_offline_remains_typed_and_exposes_queried_room_identity(status):
    with pytest.raises(TikTokOfflineError) as failure:
        resolve("123", live_room({}, status=status))
    assert failure.value.status == status and failure.value.room_id == "123"


@pytest.mark.parametrize("status", [None, "offline", True, 2.0, {}, []])
def test_malformed_room_status_is_not_confirmed_offline(status):
    with pytest.raises(TikTokResolutionError) as failure:
        resolve("123", live_room({}, status=status))
    assert not isinstance(failure.value, TikTokOfflineError)


@pytest.mark.parametrize("error", [URLError(socket.gaierror("DNS unavailable")),
    TimeoutError("timed out"), HTTPError("https://www.tiktok.com/", 503, "unavailable", {}, None)])
def test_transient_network_failure_is_not_offline(error):
    def failed(*args, **kwargs):
        raise error
    with pytest.raises(TikTokResolutionTransientError):
        resolve_live(PAGE, opener=failed)


def test_diagnostics_hide_signed_transport_and_untrusted_rendition_labels():
    result = resolve_live(PAGE, opener=_Opener([live_page(), live_room({SIGNED: SIGNED})]))
    assert SIGNED not in repr(result) and "secret" not in str(result)
    assert result.safe_diagnostics() == {"room_id": "123456", "live": True}
    assert "secret" not in json.dumps(result.safe_diagnostics())
    assert result.flv_url == SIGNED


def test_signed_values_in_malformed_identity_do_not_enter_diagnostics():
    with pytest.raises(TikTokResolutionError) as failure:
        resolve(SIGNED)
    assert SIGNED not in str(failure.value) and "secret" not in str(failure.value)


@pytest.mark.parametrize("page", [b'{"roomId":"00123"}',
    b'<a href="snssdk123://live?room_id=00123&other=value">room</a>',
    b'<script id="__NEXT_DATA__">{"room_id":"00123"}</script>'])
def test_existing_discovery_formats_have_canonical_identity(page):
    result = resolve_live(PAGE, opener=_Opener([page, live_room({"HD1": SIGNED})]))
    assert result.room_id == "123"


@pytest.mark.parametrize("body", [
    b'{"status_code":0,"data":{"stream_url":{}}}',
    b'{"status_code":0,"data":{"room":null}}',
    b'{"status_code":0,"data":{"room":[]}}',
    b'{"status_code":0,"data":{"status":2,"status":4}}',
    b'{"status_code":"https://cdn.test/secret","data":{}}',
    b'not json',
])
def test_malformed_room_info_is_not_offline_or_secret_diagnostic(body):
    with pytest.raises(TikTokResolutionError) as failure:
        resolve("123", body)
    assert not isinstance(failure.value, TikTokOfflineError)
    assert "secret" not in str(failure.value)


def test_nested_room_id_does_not_confuse_account_owner_id():
    room = {"status_code": 0, "data": {"room": {"id": "123", "status": 2,
        "owner": {"id": "999"}, "stream_url": {"flv_pull_url": {"HD1": SIGNED}}}}}
    assert resolve("123", json.dumps(room).encode()).room_id == "123"


@pytest.mark.parametrize("field", ["id", "id_str", "room_id"])
def test_malformed_echoed_room_identity_is_not_used(field):
    room = json.loads(live_room({"HD1": SIGNED}))
    room["data"][field] = ""
    with pytest.raises(TikTokResolutionError):
        resolve("123", json.dumps(room).encode())


def test_transient_error_message_redacts_urls():
    def failed(*args, **kwargs):
        raise URLError(ConnectionResetError("request failed " + SIGNED))
    with pytest.raises(TikTokResolutionTransientError) as failure:
        resolve_live(PAGE, opener=failed)
    assert SIGNED not in str(failure.value) and "secret" not in str(failure.value)


def test_identity_constructor_cannot_claim_an_offline_room_is_live():
    with pytest.raises(ValueError):
        LiveResolution("123", SIGNED, room_status=4)


def test_resolution_is_a_single_lookup_without_future_live_polling():
    opener = _Opener([live_page("123"), live_room({}, status=4)])
    with pytest.raises(TikTokOfflineError):
        resolve_live(PAGE, opener=opener)
    assert len(opener.urls) == 2


@pytest.mark.parametrize("raw", ["", "123bad", 0, None])
def test_malformed_public_lookup_identity_fails_without_offline_claim(raw):
    lookup = json.dumps({"statusCode": 0, "data": {"roomId": raw}}).encode()
    with pytest.raises(TikTokResolutionError) as failure:
        resolve_live(PAGE, opener=_Opener([b"<html></html>", lookup]))
    assert not isinstance(failure.value, TikTokOfflineError)


def test_cdn_query_cannot_supply_missing_public_room_identity():
    page = b'<video src="https://cdn.test/live.flv?room_id=123&signature=secret"></video>'
    opener = _Opener([page, b'{"statusCode":0,"data":{}}'])
    with pytest.raises(TikTokResolutionError, match="unable to determine room ID"):
        resolve_live(PAGE, opener=opener)
    assert len(opener.urls) == 2
