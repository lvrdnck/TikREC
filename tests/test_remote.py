"""Injected HTTP requests cover remote controls without sockets or live media."""

import json
from io import BytesIO
from urllib.error import HTTPError, URLError

import pytest

from tikrec.remote import RemoteClient, RemoteError, _NoRedirect


def test_health_status_monitoring_start_stop_requests():
    calls = []

    def opener(request, timeout):
        calls.append((request, timeout))
        return BytesIO(b'{"state": "recording"}')

    client = RemoteClient("http://main-pc:8765/", token="secret", opener=opener)
    assert client.health() == {"state": "recording"}
    client.status()
    client.recordings()
    client.monitoring()
    client.start("https://www.tiktok.com/@creator/live", r"C:\Videos\out.mp4", raw_copy=True)
    client.stop()
    assert [(r.get_method(), r.full_url) for r, _ in calls] == [
        ("GET", "http://main-pc:8765/health"), ("GET", "http://main-pc:8765/recording"),
        ("GET", "http://main-pc:8765/recordings"),
        ("GET", "http://main-pc:8765/monitoring"),
        ("POST", "http://main-pc:8765/recording/start"),
        ("POST", "http://main-pc:8765/recording/stop")]
    assert json.loads(calls[4][0].data)["output"] == r"C:\Videos\out.mp4"
    assert json.loads(calls[4][0].data)["raw_copy"] is True
    assert json.loads(calls[5][0].data) == {}
    assert all(r.get_header("Authorization") == "Bearer secret" and t == 10 for r, t in calls)


def test_start_omits_disabled_raw_copy_for_wire_compatibility():
    requests = []
    client = RemoteClient("http://main-pc", opener=lambda request, **_: (
        requests.append(request) or BytesIO(b'{}')
    ))
    client.start("page", "path")
    assert json.loads(requests[0].data) == {"url": "page", "output": "path"}
    with pytest.raises(ValueError, match="boolean"):
        client.start("page", "path", raw_copy=1)


def test_targeted_stop_validates_and_sends_canonical_session_id():
    requests = []
    client = RemoteClient("http://main-pc", opener=lambda request, **_: (
        requests.append(request) or BytesIO(b'{}')
    ))
    session_id = "00000000-0000-0000-0000-000000000123"
    client.stop(session_id)
    assert json.loads(requests[0].data) == {"session_id": session_id}
    with pytest.raises(ValueError, match="canonical UUID"):
        client.stop("not-a-session")


def test_ambiguous_status_and_stop_errors_direct_to_aggregate_controls():
    def opener(request, **kwargs):
        raise HTTPError(request.full_url, 409, "secret", {}, BytesIO(b"secret"))
    client = RemoteClient("http://main-pc", opener=opener)
    for operation in (client.status, client.stop):
        with pytest.raises(RemoteError, match="recordings or an explicit session ID"):
            operation()


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
