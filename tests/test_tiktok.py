from __future__ import annotations

import json
from http.client import IncompleteRead
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlsplit
import unittest
import pytest

from tikrec.tiktok import (
    TikTokOfflineError,
    TikTokResolutionError,
    TikTokResolutionTransientError,
    resolve_live_url,
)


def live_page(room_id: str = "123456") -> bytes:
    state = {"UserModule": {"users": {"creator": {"roomId": room_id}}}}
    return f'<script id="SIGI_STATE" type="application/json">{json.dumps(state)}</script>'.encode()


def live_room(
    renditions: dict[str, str],
    status: object = 2,
    rtmp_pull_url: str | None = None,
) -> bytes:
    stream_url: dict[str, object] = {"flv_pull_url": renditions}
    if rtmp_pull_url is not None:
        stream_url["rtmp_pull_url"] = rtmp_pull_url
    return json.dumps({
        "status_code": 0,
        "data": {"status": status, "stream_url": stream_url},
    }).encode()


def room_info_error(status_code: int) -> bytes:
    return json.dumps({"status_code": status_code, "data": {"prompts": ""}}).encode()


class TikTokResolverTests(unittest.TestCase):
    def test_resolves_a_public_live_url_and_discovers_its_room_id(self) -> None:
        opener = _Opener([live_page("987654"), live_room({"HD1": "https://cdn.test/live.flv?token=x"})])

        result = resolve_live_url("https://www.tiktok.com/@creator/live", opener=opener)

        self.assertEqual(result, "https://cdn.test/live.flv?token=x")
        self.assertEqual(opener.urls[0], "https://www.tiktok.com/@creator/live")
        query = parse_qs(urlsplit(opener.urls[1]).query)
        self.assertEqual(query, {"aid": ["1988"], "room_id": ["987654"]})

    def test_selects_highest_quality_flv_rendition_deterministically(self) -> None:
        opener = _Opener([live_page(), live_room({
            "SD1": "https://cdn.test/sd.flv",
            "HD1": "https://cdn.test/hd.flv",
            "FULL_HD1": "https://cdn.test/full-hd.flv",
        })])

        self.assertEqual(
            resolve_live_url("https://www.tiktok.com/@creator/live", opener=opener),
            "https://cdn.test/full-hd.flv",
        )

    def test_preserves_the_raw_live_status_for_confirmation_evidence(self) -> None:
        opener = _Opener([live_page(), live_room({"HD1": "https://cdn.test/live.flv"}, "2")])

        result = resolve_live_url("https://www.tiktok.com/@creator/live", opener=opener)

        self.assertEqual(result.room_status, "2")

    def test_preserves_selected_label_and_source_without_changing_selection(self) -> None:
        for renditions, rtmp, expected in (
            ({"HD1": "https://cdn.test/hd.flv"}, None, ("hd1", "flv_pull_url")),
            ({}, "https://cdn.test/rtmp.flv", ("default", "rtmp_pull_url")),
        ):
            opener = _Opener([live_page(), live_room(renditions, rtmp_pull_url=rtmp)])
            result = resolve_live_url("https://www.tiktok.com/@creator/live", opener=opener)
            self.assertEqual((result.rendition_label, result.rendition_source), expected)

    def test_prefers_flv_pull_url_when_quality_tiers_match(self) -> None:
        opener = _Opener([live_page(), live_room(
            {"default": "https://cdn.test/from-flv-field.flv"},
            rtmp_pull_url="https://cdn.test/from-rtmp-field.flv",
        )])

        self.assertEqual(
            resolve_live_url("https://www.tiktok.com/@creator/live", opener=opener),
            "https://cdn.test/from-flv-field.flv",
        )

    def test_uses_https_flv_from_rtmp_pull_url_when_flv_map_is_empty(self) -> None:
        opener = _Opener([live_page(), live_room(
            {}, rtmp_pull_url="https://cdn.test/live.flv?token=x"
        )])

        self.assertEqual(
            resolve_live_url("https://www.tiktok.com/@creator/live", opener=opener),
            "https://cdn.test/live.flv?token=x",
        )

    def test_rejects_an_rtmp_url_from_rtmp_pull_url(self) -> None:
        opener = _Opener([live_page(), live_room(
            {}, rtmp_pull_url="rtmp://cdn.test/live.flv"
        )])

        with self.assertRaisesRegex(
            TikTokResolutionError,
            "no public HTTP\\(S\\) FLV rendition in flv_pull_url or rtmp_pull_url",
        ):
            resolve_live_url("https://www.tiktok.com/@creator/live", opener=opener)

    def test_uses_public_room_lookup_when_page_has_no_embedded_room_id(self) -> None:
        lookup = json.dumps({"statusCode": 0, "data": {"liveRoom": {"roomId": "456"}}}).encode()
        opener = _Opener([b"<html>no room state</html>", lookup, live_room({
            "HD1": "https://cdn.test/live.flv",
        })])

        self.assertEqual(
            resolve_live_url("https://www.tiktok.com/@creator/live", opener=opener),
            "https://cdn.test/live.flv",
        )
        lookup_query = parse_qs(urlsplit(opener.urls[1]).query)
        self.assertEqual(lookup_query, {
            "aid": ["1988"], "uniqueId": ["creator"], "sourceType": ["54"],
        })
        self.assertEqual(parse_qs(urlsplit(opener.urls[2]).query)["room_id"], ["456"])

    def test_reports_a_room_that_is_not_live(self) -> None:
        opener = _Opener([live_page(), live_room({}, status=4)])

        with self.assertRaisesRegex(TikTokOfflineError, "not live") as raised:
            resolve_live_url("https://www.tiktok.com/@creator/live", opener=opener)

        self.assertEqual(raised.exception.status, 4)

    def test_reports_4003110_as_anonymous_stream_access_restriction(self) -> None:
        opener = _Opener([live_page(), room_info_error(4003110)])

        with self.assertRaisesRegex(
            TikTokResolutionError,
            "stream is not available to anonymous requests.*4003110",
        ):
            resolve_live_url("https://www.tiktok.com/@creator/live", opener=opener)

    def test_reports_missing_flv_renditions(self) -> None:
        opener = _Opener([live_page(), live_room({"HD1": "https://cdn.test/live.m3u8"})])

        with self.assertRaisesRegex(TikTokResolutionError, "no public HTTP\\(S\\) FLV"):
            resolve_live_url("https://www.tiktok.com/@creator/live", opener=opener)

    def test_reports_malformed_room_info_json(self) -> None:
        opener = _Opener([live_page(), b"not json"])

        with self.assertRaisesRegex(TikTokResolutionError, "malformed room-info JSON"):
            resolve_live_url("https://www.tiktok.com/@creator/live", opener=opener)

    def test_reports_a_live_page_without_a_room_id(self) -> None:
        opener = _Opener([b"<html>no public state</html>", b'{"statusCode": 0, "data": {}}'])

        with self.assertRaisesRegex(TikTokResolutionError, "unable to determine room ID"):
            resolve_live_url("https://www.tiktok.com/@creator/live", opener=opener)

    def test_rejects_invalid_input_before_requesting_tiktok(self) -> None:
        opener = _Opener([])

        with self.assertRaisesRegex(TikTokResolutionError, "unsupported or malformed"):
            resolve_live_url("https://example.test/@creator/live", opener=opener)

        self.assertEqual(opener.urls, [])

    def test_reports_network_failures(self) -> None:
        def failing_opener(*_: object, **__: object):
            raise URLError(ConnectionRefusedError("connection refused"))

        with self.assertRaisesRegex(TikTokResolutionTransientError, "network request failed"):
            resolve_live_url("https://www.tiktok.com/@creator/live", opener=failing_opener)

    def test_classifies_a_short_read_of_the_live_page_as_transient(self) -> None:
        opener = _Opener([IncompleteRead(b"partial page", 20)])

        with self.assertRaises(TikTokResolutionTransientError):
            resolve_live_url("https://www.tiktok.com/@creator/live", opener=opener)

    def test_classifies_a_short_read_of_the_room_id_lookup_as_transient(self) -> None:
        opener = _Opener([
            b"<html>no public state</html>",
            IncompleteRead(b"partial lookup", 20),
        ])

        with self.assertRaises(TikTokResolutionTransientError):
            resolve_live_url("https://www.tiktok.com/@creator/live", opener=opener)

    def test_classifies_a_short_read_of_room_info_as_transient(self) -> None:
        opener = _Opener([live_page(), IncompleteRead(b"partial room info", 20)])

        with self.assertRaises(TikTokResolutionTransientError):
            resolve_live_url("https://www.tiktok.com/@creator/live", opener=opener)


class _Opener:
    def __init__(self, responses: list[bytes | Exception]) -> None:
        self._responses = iter(responses)
        self.urls: list[str] = []

    def __call__(self, request, **_: object) -> _Response:
        self.urls.append(request.full_url)
        return _Response(next(self._responses))


class _Response:
    def __init__(self, body: bytes | Exception) -> None:
        self._body = body

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def read(self) -> bytes:
        if isinstance(self._body, Exception):
            raise self._body
        return self._body


@pytest.mark.parametrize("code", [408, 425, 429, 500, 502, 503, 504, 400, 403, 404])
def test_public_http_boundary_preserves_retryability_and_safe_wait_hint(code):
    signed = "https://cdn.test/live.flv?secret=hidden"
    error = HTTPError(signed, code, signed, {"Retry-After": "60"}, None)
    expected = TikTokResolutionTransientError if code >= 500 or code in {408, 425, 429} else TikTokResolutionError
    with pytest.raises(expected) as caught:
        resolve_live_url("https://www.tiktok.com/@creator/live", opener=_Opener([error]))
    assert isinstance(caught.value, TikTokResolutionTransientError) == (expected is TikTokResolutionTransientError)
    assert "secret" not in str(caught.value)
    if expected is TikTokResolutionTransientError:
        assert caught.value.kind == "http" and caught.value.retry_after == 60


def test_public_http_boundary_does_not_retry_local_permission_failure():
    with pytest.raises(TikTokResolutionError) as caught:
        resolve_live_url("https://www.tiktok.com/@creator/live", opener=_Opener([PermissionError("denied")]))
    assert not isinstance(caught.value, TikTokResolutionTransientError)


if __name__ == "__main__":
    unittest.main()
