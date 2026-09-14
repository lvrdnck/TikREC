"""Explicit offline failure classifications from concrete urllib/socket shapes."""

import errno
import socket
from http.client import IncompleteRead
from urllib.error import HTTPError, URLError

import pytest

from tikrec.capture_control import CaptureStopped
from tikrec.live_support import LiveChangedError
from tikrec.network_errors import classify_failure
from tikrec.tiktok import TikTokOfflineError, TikTokResolutionError, TikTokResolutionTransientError


@pytest.mark.parametrize("error,kind", [
    (socket.gaierror(socket.EAI_AGAIN, "DNS"), "dns"),
    (URLError(socket.gaierror(socket.EAI_NONAME, "DNS")), "dns"),
    (socket.timeout("timeout"), "timeout"), (ConnectionResetError(), "connection"),
    (ConnectionAbortedError(), "connection"), (ConnectionRefusedError(), "connection"),
    (IncompleteRead(b"tail"), "connection"), (EOFError(), "connection"),
    (OSError(errno.ENETUNREACH, "internet lost"), "connection"),
    (TikTokResolutionTransientError("failed", kind="https://cdn.test/a?secret"), "network"),
])
def test_concrete_network_errors_are_transient(error, kind):
    result = classify_failure(error)
    assert result.category == "transient" and result.reason == kind
    assert "secret" not in repr(result)


@pytest.mark.parametrize("code", [408, 425, 429, 500, 502, 503, 504, 599])
def test_temporary_http_status_is_retryable(code):
    error = HTTPError("https://cdn.test/a.flv?secret", code, "failed", {"Retry-After": "60"}, None)
    result = classify_failure(error)
    assert result.category == "transient" and result.retry_after == 60
    assert "secret" not in repr(result)


@pytest.mark.parametrize("error,category", [
    (PermissionError(errno.EACCES, "denied"), "local"),
    (OSError(errno.ENOSPC, "disk full"), "local"), (ValueError("programming"), "local"),
    (OSError("writer failed"), "local"), (URLError("unknown transport cause"), "local"),
    (TikTokResolutionError("malformed room"), "malformed"),
    (HTTPError("url", 404, "missing", {}, None), "malformed"),
    (HTTPError("url", 403, "denied", {}, None), "malformed"),
    (TikTokOfflineError("offline"), "terminal"), (LiveChangedError(), "terminal"),
    (CaptureStopped(), "stop"), (KeyboardInterrupt(), "stop"),
])
def test_non_network_states_are_not_retried(error, category):
    assert classify_failure(error).category == category


@pytest.mark.parametrize("header,expected", [
    ("Wed, 01 Jan 2025 00:01:00 GMT", 60), ("bad", None), ("-3", None), ("0", 0),
])
def test_retry_after_dates_and_malformed_hints(header, expected):
    error = HTTPError("url", 503, "failed", {"Retry-After": header}, None)
    assert classify_failure(error, now=1735689600).retry_after == expected
