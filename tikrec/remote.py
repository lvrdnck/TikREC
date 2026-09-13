"""Small JSON client for a trusted TikREC service, with injectable HTTP I/O."""

from __future__ import annotations

import json
from collections.abc import Callable
from http.client import HTTPException
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener


class RemoteError(RuntimeError):
    """A service request failed or returned an invalid response."""


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, newurl):
        # Do not forward a bearer secret to a redirect target or retry a start there.
        return None


class RemoteClient:
    """Send only health/status/start/stop requests to an explicit server address."""

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

    def start(self, url: str, output: str) -> dict:
        """Request one recording using an output path on the service machine."""
        return self._request("POST", "/recording/start", {"url": url, "output": output})

    def stop(self) -> dict:
        """Request graceful capture stop; finalization continues on the service."""
        return self._request("POST", "/recording/stop", {})

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
            hint = {401: "check bearer token", 409: "recording already active",
                    400: "check public LIVE URL and unused absolute .mp4 output"}.get(code, "request rejected")
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
