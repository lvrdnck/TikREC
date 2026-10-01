"""Managed endpoints share service authentication and strict bounded parsing."""

from email.message import Message
from io import BytesIO
from types import SimpleNamespace

import pytest

from tikrec.managed_http import handle_managed
from tikrec.managed_registry import installed


def handler(body, **headers):
    """Construct the bounded request surface without opening a network socket."""
    message = Message()
    message["Content-Type"] = "application/json"
    message["Content-Length"] = str(len(body))
    for key, value in headers.items():
        message[key] = value
    replies = []
    return SimpleNamespace(path="/managed/retention/preview", headers=message,
                           rfile=BytesIO(body), _json=lambda *args: replies.append(args)), replies


def test_unmanaged_service_has_no_managed_route():
    request, replies = handler(b"{}")
    assert handle_managed(request)
    assert replies[0][0] == 404


@pytest.mark.parametrize("body", [b"[]", b"{", b'{"session_id":"a","session_id":"b"}'])
def test_invalid_json_and_duplicate_fields_refused(body):
    request, replies = handler(body)
    with installed(object()):
        assert handle_managed(request)
    assert replies[0][0] == 400


def test_duplicate_length_and_transfer_encoding_refused():
    for headers in [{"Content-Length": "2"}, {"Transfer-Encoding": "chunked"}]:
        request, replies = handler(b"{}", **headers)
        with installed(object()):
            assert handle_managed(request)
        assert replies[0][0] == 400


def test_bounded_route_delegates_once(monkeypatch):
    import tikrec.managed_http as http
    calls = []
    monkeypatch.setitem(http._ROUTES, "/managed/retention/preview",
                        lambda authority, body: calls.append(body) or {"preview": "read-only"})
    request, replies = handler(b'{"session_id":"value"}')
    with installed(object()):
        assert handle_managed(request)
    assert calls == [{"session_id": "value"}] and replies == [(200, {"preview": "read-only"})]
