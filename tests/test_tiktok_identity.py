"""Offline checks for public room identity discovery and safe comparisons."""

import pytest

from tikrec.tiktok_identity import find_room_id, room_id_from_page


def test_finds_nested_public_room_id():
    assert find_room_id({"data": [{"roomId": 123456}]}) == "123456"


def test_page_without_identity_returns_none():
    assert room_id_from_page(b"<html>no public state</html>") is None


def test_page_state_preserves_room_id():
    assert room_id_from_page(b'<script id="SIGI_STATE">{"roomId":"456"}</script>') == "456"


def test_invalid_page_encoding_fails():
    with pytest.raises(ValueError, match="not valid UTF-8"):
        room_id_from_page(b"\xff")
