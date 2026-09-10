from __future__ import annotations

import json
from urllib.error import URLError
from urllib.parse import parse_qs, urlsplit
import unittest

from tikrec.tiktok import TikTokResolutionError, resolve_live_url


def live_page(room_id: str = "123456") -> bytes:
    state = {"UserModule": {"users": {"creator": {"roomId": room_id}}}}
    return f'<script id="SIGI_STATE" type="application/json">{json.dumps(state)}</script>'.encode()


def live_room(renditions: dict[str, str], status: int = 2) -> bytes:
    return json.dumps({
        "status_code": 0,
        "data": {"status": status, "stream_url": {"flv_pull_url": renditions}},
    }).encode()


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

        with self.assertRaisesRegex(TikTokResolutionError, "not live"):
            resolve_live_url("https://www.tiktok.com/@creator/live", opener=opener)

    def test_reports_missing_flv_renditions(self) -> None:
        opener = _Opener([live_page(), live_room({"HD1": "https://cdn.test/live.m3u8"})])

        with self.assertRaisesRegex(TikTokResolutionError, "no public FLV"):
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
            raise URLError("connection refused")

        with self.assertRaisesRegex(TikTokResolutionError, "network request failed"):
            resolve_live_url("https://www.tiktok.com/@creator/live", opener=failing_opener)


class _Opener:
    def __init__(self, responses: list[bytes]) -> None:
        self._responses = iter(responses)
        self.urls: list[str] = []

    def __call__(self, request, **_: object) -> _Response:
        self.urls.append(request.full_url)
        return _Response(next(self._responses))


class _Response:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def read(self) -> bytes:
        return self._body


if __name__ == "__main__":
    unittest.main()
