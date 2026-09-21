"""Narrow trusted-network HTTP/JSON recording controls using the stdlib."""

from __future__ import annotations

import hmac
import ipaddress
import json
import socket
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .recording import RecordingBusy, RecordingController
from .job_state import JobStateStore
from .service_job import default_job_state_path


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
MAX_BODY = 8192


def validate_bind(host: str, token: str | None) -> str:
    """Require explicit IP binding and a secret for all non-loopback addresses."""
    host = DEFAULT_HOST if host == "localhost" else host
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        raise ValueError("host must be a loopback, LAN, or Tailscale IP address") from None
    if token is not None and (not 16 <= len(token) <= 512
                              or any(not 33 <= ord(c) <= 126 for c in token)):
        raise ValueError("token must contain 16–512 printable ASCII characters without spaces")
    if not address.is_loopback and token is None:
        raise ValueError("non-loopback binding requires TIKREC_TOKEN or --token-file")
    return str(address)


class RecordingHTTPServer(ThreadingHTTPServer):
    """Serve requests separately from the single application recording worker."""

    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT, *,
                 controller: RecordingController | None = None,
                 token: str | None = None, bind_and_activate: bool = True) -> None:
        host = validate_bind(host, token)
        if not 0 <= port <= 65535:
            raise ValueError("port must be between 0 and 65535")
        self.token = token
        # Explicit IPv6 loopback/tailnet binding uses the appropriate socket family.
        self.address_family = socket.AF_INET6 if ":" in host else socket.AF_INET
        super().__init__((host, port), RecordingHandler, bind_and_activate=bind_and_activate)
        try:
            # Reserve the listening address before recovery can open a second media writer.
            self.controller = controller if controller is not None else RecordingController(
                store=JobStateStore(default_job_state_path()))
        except BaseException:
            self.server_close()
            raise


class RecordingHandler(BaseHTTPRequestHandler):
    """Handle only four JSON routes; never serve files or execute caller commands."""

    server: RecordingHTTPServer
    server_version = "TikREC"
    sys_version = ""

    def setup(self) -> None:
        """Bound idle header/body reads so a stalled client cannot wait forever."""
        super().setup()
        self.connection.settimeout(10)

    def log_message(self, format: str, *args: object) -> None:
        """Suppress raw request logging, which could include secrets or URLs."""

    def send_error(self, code: int, message: str | None = None,
                   explain: str | None = None) -> None:
        """Keep parser and unsupported-method errors JSON and free of reflected input."""
        self._json(code, {"error": "unsupported or malformed HTTP request"})

    def do_GET(self) -> None:
        """Return health or the latest recording snapshot."""
        if not self._authorized():
            return
        if self.path == "/health":
            self._json(200, self.server.controller.health())
        elif self.path == "/recording":
            self._json(200, self.server.controller.status())
        else:
            self._json(404, {"error": "unknown endpoint"})

    def do_POST(self) -> None:
        """Validate a bounded JSON object and delegate lifecycle to the controller."""
        if not self._authorized():
            return
        if self.path not in {"/recording/start", "/recording/stop"}:
            self._json(404, {"error": "unknown endpoint"})
            return
        if self.headers.get_content_type() != "application/json":
            self._json(415, {"error": "Content-Type must be application/json"})
            return
        if self.headers.get("Transfer-Encoding") is not None:
            self._json(400, {"error": "transfer encoding is unsupported"})
            return
        lengths = self.headers.get_all("Content-Length", [])
        if len(lengths) != 1:
            self._json(411, {"error": "one Content-Length is required"})
            return
        try:
            size = int(lengths[0])
        except ValueError:
            size = -1
        if not 0 < size <= MAX_BODY:
            self._json(413, {"error": "JSON body must be 1–8192 bytes"})
            return
        try:
            body = json.loads(self.rfile.read(size))
        except (ValueError, OSError):
            self._json(400, {"error": "invalid JSON body"})
            return
        if not isinstance(body, dict):
            self._json(400, {"error": "JSON body must be an object"})
            return
        if self.path == "/recording/stop":
            if body:
                self._json(400, {"error": "stop requires an empty JSON object"})
                return
            self._json(202, self.server.controller.stop())
            return
        fields = set(body)
        if (fields not in ({"url", "output"}, {"url", "output", "raw_copy"})
                or not isinstance(body.get("url"), str)
                or not isinstance(body.get("output"), str)
                or ("raw_copy" in body and type(body["raw_copy"]) is not bool)):
            self._json(400, {"error": "start requires string url/output and optional boolean raw_copy"})
            return
        try:
            if body.get("raw_copy", False):
                status = self.server.controller.start(body["url"], body["output"], raw_copy=True)
            else:
                # Preserve the original call shape for ordinary/default starts.
                status = self.server.controller.start(body["url"], body["output"])
        except RecordingBusy:
            self._json(409, {"error": "recording active, recovery unresolved, or service shutting down"})
        except (ValueError, OSError):
            # Fixed validation errors avoid reflecting arbitrary request content or secrets.
            self._json(400, {"error": "invalid LIVE page or absolute .mp4 output; "
                                     "output and retained parts must not already exist"})
        except Exception:
            self._json(500, {"error": "could not start recording worker"})
        else:
            self._json(202, status)

    def _authorized(self) -> bool:
        # No browser UI exists; refuse cross-origin browser requests even on loopback.
        if self.headers.get("Origin") is not None:
            self._json(403, {"error": "browser-origin requests are unsupported"})
            return False
        if self.server.token is not None:
            supplied = self.headers.get("Authorization", "").encode("utf-8")
            expected = f"Bearer {self.server.token}".encode("ascii")
            if not hmac.compare_digest(supplied, expected):
                self._json(401, {"error": "bearer token required"})
                return False
        return True

    def _json(self, status: int, value: dict) -> None:
        body = json.dumps(value, allow_nan=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)
        self.close_connection = True


def serve(*, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT,
          token: str | None = None, controller: RecordingController | None = None) -> None:
    """Run until local interruption, then cooperatively finish the current job."""
    with RecordingHTTPServer(host, port, token=token, controller=controller) as server:
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.controller.shutdown()
