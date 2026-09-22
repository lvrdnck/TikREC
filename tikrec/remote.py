"""Small JSON client for a trusted TikREC service, with injectable HTTP I/O."""

from __future__ import annotations

import json
from collections.abc import Callable
from http.client import HTTPException
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener
from uuid import UUID


class RemoteError(RuntimeError):
    """A service request failed or returned an invalid response."""


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, newurl):
        # Do not forward a bearer secret to a redirect target or retry a start there.
        return None


class RemoteClient:
    """Send only bounded recording-control requests to an explicit server."""

    def __init__(self, server: str, *, token: str | None = None,
                 opener: Callable | None = None, timeout: float = 10) -> None:
        parsed = urlsplit(server)
        if (parsed.scheme not in {"http", "https"} or not parsed.hostname
                or parsed.username is not None or parsed.password is not None
                or parsed.path not in {"", "/"} or parsed.query or parsed.fragment):
            raise ValueError("server must be an http(s) address without credentials or a path")
        try:
            parsed.port
        except ValueError:
            raise ValueError("invalid server port") from None
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        self._server = server.rstrip("/")
        self._token = token
        self._timeout = timeout
        # Tailnet traffic stays direct rather than entering an environment-configured proxy.
        self._opener = opener or build_opener(ProxyHandler({}), _NoRedirect()).open

    def health(self) -> dict:
        """Check service health and availability."""
        return self._request("GET", "/health")

    def status(self) -> dict:
        """Fetch current recording progress or the most recent result."""
        return self._request("GET", "/recording")

    def recordings(self) -> dict:
        """Fetch aggregate recording capacity and one safe status per slot."""
        return self._request("GET", "/recordings")

    def monitoring(self) -> dict:
        """Fetch the service's sanitized in-memory creator observations."""
        return self._request("GET", "/monitoring")

    def start(self, url: str, output: str, *, raw_copy: bool = False) -> dict:
        """Request one recording, optionally retaining co-located raw diagnostics."""
        if type(raw_copy) is not bool:
            raise ValueError("raw_copy must be a boolean")
        body = {"url": url, "output": output}
        if raw_copy:
            # Omit the disabled option so ordinary requests remain wire-compatible.
            body["raw_copy"] = True
        return self._request("POST", "/recording/start", body)

    def stop(self, session_id: str | None = None) -> dict:
        """Request graceful stop for the sole active or one explicit session."""
        body = {} if session_id is None else {"session_id": _session_id(session_id)}
        return self._request("POST", "/recording/stop", body)

    def _request(self, method: str, path: str, body: dict | None = None) -> dict:
        data = None if body is None else json.dumps(body).encode("utf-8")
        headers = {"Accept": "application/json"}
        if data is not None:
            headers["Content-Type"] = "application/json"
        if self._token is not None:
            headers["Authorization"] = f"Bearer {self._token}"
        request = Request(self._server + path, data=data, headers=headers, method=method)
        try:
            with self._opener(request, timeout=self._timeout) as response:
                raw = response.read(65537)
        except HTTPError as error:
            code = error.code
            error.close()
            # Never echo an arbitrary remote error page that could contain a secret.
            if code == 409 and path == "/recording/start":
                hint = "recording capacity is unavailable"
            elif code == 409:
                hint = "multiple recordings active; use recordings or an explicit session ID"
            elif code == 404 and path == "/recording/stop":
                hint = "active session not found"
            else:
                hint = {401: "check bearer token",
                        400: "check request values and absolute .mp4 output"}.get(
                            code, "request rejected")
            raise RemoteError(f"service HTTP {code}: {hint}") from None
        except (OSError, URLError, HTTPException):
            # A lost start response is ambiguous; automatically retrying could start two jobs.
            raise RemoteError("service request failed; check connectivity and query status before retrying") from None
        try:
            if len(raw) > 65536:
                raise ValueError("too large")
            result = json.loads(raw)
            if not isinstance(result, dict):
                raise ValueError("not an object")
        except ValueError:
            raise RemoteError("service returned invalid JSON") from None
        return result


def _session_id(value: object) -> str:
    try:
        canonical = str(UUID(value))
    except (TypeError, ValueError, AttributeError):
        raise ValueError("session_id must be a canonical UUID") from None
    if value != canonical:
        raise ValueError("session_id must be a canonical UUID")
    return canonical
