"""Patient identity resolution inside the service's existing reconciliation worker."""

from .capture_control import CaptureStopped
from .network_errors import classify_failure
from .retry_policy import OutageRecovery, RecoveryExhausted
from .tiktok import LiveResolution, _is_http_flv_url


def resolve_startup_patiently(resolver, url, *, policy, control, clock, wall_clock, notify):
    """Retry only transport failures; stop/end/malformed errors escape immediately."""
    recovery = OutageRecovery(policy, clock=clock, wall_clock=wall_clock)
    while True:
        try:
            resolution = control.resolve(resolver, url)
        except (CaptureStopped, KeyboardInterrupt):
            if recovery.active:
                notify("user_stop", recovery)
            raise
        except Exception as error:
            classification = classify_failure(error, transport=True, now=wall_clock())
            if classification.category != "transient":
                if recovery.active:
                    phase = "offline" if classification.reason == "room_ended" else "failed"
                    notify(phase, recovery)
                raise
            entered = not recovery.active
            recovery.failure(error, transport=True)
            if entered:
                notify("entered", recovery)
        else:
            if (not isinstance(resolution, LiveResolution) or not isinstance(resolution.flv_url, str)
                    or not _is_http_flv_url(resolution.flv_url)):
                if recovery.active:
                    notify("failed", recovery)
                raise ValueError("startup resolver did not establish structured public LIVE identity")
            if recovery.active:
                notify("recovered", recovery)
            return resolution
        try:
            notify("wait", recovery)
            recovery.wait(control)
        except RecoveryExhausted:
            notify("exhausted", recovery)
            raise
        except (CaptureStopped, KeyboardInterrupt):
            notify("user_stop", recovery)
            raise
