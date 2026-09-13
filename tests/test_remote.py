"""Injected HTTP requests cover remote controls without sockets or live media."""

import json
from io import BytesIO
from urllib.error import HTTPError, URLError

import pytest

from tikrec.remote import RemoteClient, RemoteError, _NoRedirect


def test_health_status_start_stop_requests():
    calls = []

    def opener(request, timeout):
        calls.append((request, timeout))
        return BytesIO(b'{"state": "recording"}')

    client = RemoteClient("http://main-pc:8765/", token="secret", opener=opener)
    assert client.health() == {"state": "recording"}
    client.status()
    client.start("https://www.tiktok.com/@creator/live", r"C:\Videos\out.mp4")
    client.stop()
    assert [(r.get_method(), r.full_url) for r, _ in calls] == [
        ("GET", "http://main-pc:8765/health"), ("GET", "http://main-pc:8765/recording"),
        ("POST", "http://main-pc:8765/recording/start"), ("POST", "http://main-pc:8765/recording/stop")]
    assert json.loads(calls[2][0].data)["output"] == r"C:\Videos\out.mp4"
    assert json.loads(calls[3][0].data) == {}
    assert all(r.get_header("Authorization") == "Bearer secret" and t == 10 for r, t in calls)


@pytest.mark.parametrize("code", [400, 401, 409, 500])
def test_http_failure_does_not_echo_response_secret(code):
    def opener(request, **kwargs):
        raise HTTPError(request.full_url, code, "secret", {}, BytesIO(b"secret"))
    with pytest.raises(RemoteError, match=f"HTTP {code}") as failure:
        RemoteClient("http://main-pc", opener=opener).stop()
    assert "secret" not in str(failure.value)


def test_connectivity_failure_does_not_retry_start():
    calls = []
    def opener(request, **kwargs):
        calls.append(True)
        raise URLError("secret")
    with pytest.raises(RemoteError, match="query status"):
        RemoteClient("http://main-pc", opener=opener).start("page", "path")
    assert calls == [True]


@pytest.mark.parametrize("raw", [b"broken", b"[]", b"x" * 65537],
                         ids=["malformed", "array", "oversized"])
def test_invalid_json(raw):
    with pytest.raises(RemoteError, match="invalid JSON"):
        RemoteClient("http://main-pc", opener=lambda *a, **k: BytesIO(raw)).status()


@pytest.mark.parametrize("server", ["ftp://main-pc", "http://user:secret@main-pc",
                                     "http://main-pc/path", "http://main-pc?token=secret",
                                     "http://main-pc:bad"])
def test_invalid_server(server):
    with pytest.raises(ValueError):
        RemoteClient(server)


def test_redirects_are_refused():
    assert _NoRedirect().redirect_request(None, None, 302, "", {}, "http://evil.test") is None
