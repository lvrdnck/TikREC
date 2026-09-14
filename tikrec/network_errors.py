"""Classify TikREC transport failures without treating local errors as outages."""

import errno
import socket
from dataclasses import dataclass
from datetime import timezone
from email.utils import parsedate_to_datetime
from http.client import IncompleteRead, RemoteDisconnected
from urllib.error import HTTPError, URLError


@dataclass(frozen=True)
class FailureClassification:
    """Fixed safe category plus optional server wait hint; no exception text."""

    category: str
    reason: str
    retry_after: float | None = None


def classify_failure(error, *, transport=False, now=0.0):
    """Separate LIVE end, user stop, network failure, malformed data and local bugs."""
    from .capture_control import CaptureStopped
    from .live_support import LiveChangedError
    from .tiktok import TikTokOfflineError, TikTokResolutionError, TikTokResolutionTransientError
    if isinstance(error, (CaptureStopped, KeyboardInterrupt)):
        return FailureClassification("stop", "user_stop")
    if isinstance(error, (TikTokOfflineError, LiveChangedError)):
        return FailureClassification("terminal", "room_ended" if isinstance(error, TikTokOfflineError)
                                     else "live_changed")
    if isinstance(error, HTTPError):
        retryable = error.code in {408, 425, 429} or 500 <= error.code <= 599
        hint = _retry_after(error.headers.get("Retry-After"), now) if error.headers else None
        return FailureClassification("transient" if retryable else "malformed", "http", hint)
    if isinstance(error, URLError):
        # urllib wraps gaierror/timeouts in reason; never infer a network cause from text.
        return classify_failure(error.reason, transport=transport, now=now)
    if isinstance(error, TikTokResolutionTransientError):
        kind = getattr(error, "kind", "network")
        # Injected typed errors must not turn arbitrary diagnostics into public status fields.
        if not isinstance(kind, str) or kind not in {"dns", "timeout", "connection", "http", "network"}:
            kind = "network"
        return FailureClassification("transient", kind, getattr(error, "retry_after", None))
    if isinstance(error, socket.gaierror):
        return FailureClassification("transient", "dns")
    if isinstance(error, TimeoutError):
        return FailureClassification("transient", "timeout")
    if isinstance(error, (ConnectionError, IncompleteRead, RemoteDisconnected, EOFError)):
        return FailureClassification("transient", "connection")
    if isinstance(error, OSError):
        network_codes = {errno.ENETDOWN, errno.ENETUNREACH, errno.EHOSTUNREACH,
                         errno.ECONNRESET, errno.ECONNABORTED, errno.ECONNREFUSED,
                         errno.ETIMEDOUT, errno.EPIPE}
        windows_codes = {10050, 10051, 10053, 10054, 10060, 10061, 10065, 11001, 11002}
        if error.errno in network_codes or getattr(error, "winerror", None) in windows_codes:
            return FailureClassification("transient", "connection")
        # Some injected/HTTP sources raise bare OSError; only the transport boundary permits it.
        if transport and type(error) is OSError and error.errno is None:
            return FailureClassification("transient", "network")
    if isinstance(error, TikTokResolutionError):
        return FailureClassification("malformed", "resolution")
    return FailureClassification("local", "local_failure")


def _retry_after(value, now):
    if not isinstance(value, str):
        return None
    value = value.strip()
    if value.isascii() and value.isdecimal():
        # Bound parsing before float conversion so arbitrarily large headers stay harmless.
        return float(value) if len(value) < 10 else 1e9
    try:
        stamp = parsedate_to_datetime(value)
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=timezone.utc)
        return max(0.0, stamp.timestamp() - now)
    except (ValueError, TypeError, OverflowError):
        return None
