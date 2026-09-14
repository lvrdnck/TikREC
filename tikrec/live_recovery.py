"""Bind reconnects to one LIVE and adapt the shared patient policy to capture."""

import time
from .capture import CaptureError
from .live_support import LiveChangedError, _safe_reason
from .network_errors import classify_failure
from .network_evidence import append_network_record
from .retry_policy import OutageRecovery
from .tiktok import (LiveResolution, TikTokResolutionError, TikTokResolutionTransientError,
                     _ResolvedLiveUrl, _is_http_flv_url)


class OutageCaptureError(CaptureError):
    """Capture certainty is unproven; retain parts without finalizing at exhaustion."""


class SourceNetworkError(RuntimeError):
    """A retryable failure known to originate inside source creation/read, not the writer."""

    def __init__(self, error):
        super().__init__(_safe_reason(error))
        self.failure = classify_failure(error, transport=True)
        self.original = error


def resolve_bound_live(resolver, url, room_id, *, wall_clock=time.time):
    """Resolve once and refuse missing/different identity after a real room was chosen."""
    try:
        result = resolver(url)
    except Exception as error:
        failure = classify_failure(error, transport=True, now=wall_clock())
        if failure.category == "transient" and not isinstance(error, TikTokResolutionTransientError):
            raise TikTokResolutionTransientError(_safe_reason(error), kind=failure.reason,
                                                 retry_after=failure.retry_after) from error
        raise
    if isinstance(result, LiveResolution):
        result = _ResolvedLiveUrl(result.flv_url, result.room_status, result.rendition_label,
                                  result.rendition_source, result.room_id)
    if room_id is not None:
        current_id = getattr(result, "room_id", None)
        if current_id is None:
            raise TikTokResolutionError("reconnect cannot prove prior LIVE identity")
        if current_id != room_id:
            raise LiveChangedError("prior LIVE ended; account has a different room")
    if room_id is not None and (not isinstance(result, str) or not _is_http_flv_url(result)):
        raise TikTokResolutionError("resolver did not supply public HTTP(S) FLV transport")
    return result


class LiveRecovery:
    """Own episode evidence/status while keeping retry mathematics shared with startup."""

    def __init__(self, policy, *, clock, wall_clock, directory, manifest, observer):
        self.outage = OutageRecovery(policy, clock=clock, wall_clock=wall_clock)
        self.directory, self.manifest = directory, manifest
        self.wall_clock, self.observer = wall_clock, observer

    def notify(self, phase):
        """Publish fixed progress; lifecycle boundaries alone are appended to disk."""
        if self.observer is not None:
            self.observer({**self.outage.status(), "phase": phase})
        if self.manifest.active and phase != "wait":
            append_network_record(self.directory / "connections.jsonl", timestamp=self.wall_clock(),
                session_id=self.manifest.snapshot()["session_id"], phase=phase, recovery=self.outage)

    def failure(self, error):
        """Enter an outage on first failure; repeated errors only update counters."""
        entered = not self.outage.active
        if isinstance(error, SourceNetworkError):
            error = error.original
        self.outage.failure(error, transport=True)
        if entered:
            self.notify("entered")

    def end(self, phase):
        """Close the summary on useful media, proven end, user stop or failure."""
        if self.outage.active:
            self.notify(phase)
            self.outage.reset()
        elif phase in {"offline", "live_changed", "user_stop"} and self.observer is not None:
            # Proven end/stop intent matters even when no network outage preceded it.
            self.observer({**self.outage.status(), "phase": phase})
