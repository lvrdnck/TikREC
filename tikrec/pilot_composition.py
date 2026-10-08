"""One opt-in composition of existing runtime/HTTP/admission; no legacy authority."""
from threading import Lock

from .admission import RecordingAdmission
from .automation import AutomationCoordinator
from .monitoring import CreatorMonitor
from .media import inspect_media
from .pilot_limits import MAX_SESSIONS
from .recording import RecordingBusy
from .service_http_projection import RuntimeHTTPController
from .service_http_runtime import IsolatedRecordingHTTPServer
from .service_runtime import IsolatedServiceRuntime
from .storage_status import StorageStatus


def source_options(envelope, bridge, ffprobe):
    """Supply limited normal ingress and the explicit inspector (trusted fixture seam)."""
    return {**envelope.source_options(bridge),
            'media_inspector': lambda path: inspect_media(path, ffprobe=str(ffprobe))}


class PilotController(RuntimeHTTPController):
    """Manual start restrictions delegate once to the existing UUID authority."""

    def __init__(self, runtime, envelope):
        super().__init__(runtime)
        self.envelope, self.start_lock = envelope, Lock()

    def health(self):
        """Make pilot admission restrictions visible without inventing capture capacity."""
        value = super().health()
        count = len(self.runtime.journal.history(limit=9))
        free = self.envelope.free()
        value['pilot'] = {'lifetime_sessions': count, 'lifetime_limit': MAX_SESSIONS}
        if count >= MAX_SESSIONS:
            value.update(admission_available=False, admission_reason='pilot_lifetime_limit')
        elif free is None or free < 16 * 1024**3:
            value.update(admission_available=False, admission_reason='low_free_space')
        return value

    def start(self, url, output, *, raw_copy=False):
        """Bound lifetime history across slot reuse/restart without refunding any intent."""
        with self.start_lock:
            if len(self.runtime.journal.history(limit=9)) >= MAX_SESSIONS:
                raise RecordingBusy('pilot lifetime session limit reached')
            free = self.envelope.free()
            if free is None or free < 16 * 1024**3:
                raise RecordingBusy('low_free_space')
            if self.runtime.paused:
                raise RecordingBusy('pilot paused; preserve state')
            return super().start(url, output, raw_copy=raw_copy)


def compose(owner, options, token):
    """Register passive runtime before binding and preserve attached startup owners."""
    state, envelope = owner.state, owner.envelope
    storage = StorageStatus(state.home / 'media', 16, disk_usage=envelope.disk_usage)
    owner.runtime = IsolatedServiceRuntime(state.journal, state.home / 'media',
        ffmpeg=options.ffmpeg, ffprobe=options.ffprobe, storage_status=storage,
        catalog_storage=StorageStatus(state.home / 'state', 16, disk_usage=envelope.disk_usage),
        observations=lambda bridge: source_options(envelope, bridge, options.ffprobe),
        settlement_options={'candidate_limit_bytes': 256 * 1024**2}, authority_cleanup_guards=True)
    admission = RecordingAdmission(owner.runtime.root, owner.runtime.health, storage_status=storage)
    automation = AutomationCoordinator(owner.runtime, admission, state.automation)
    # Empty creator set/no loader means no monitor thread, source discovery or automation.
    automation.stop()
    monitor = CreatorMonitor((), cycle_completed=automation.cycle_completed)
    try:
        owner.server = IsolatedRecordingHTTPServer('127.0.0.1', options.port,
            runtime=owner.runtime, admission=admission, automation=automation,
            monitor=monitor, token=token, request_grace=1)
    except BaseException as error:
        owner.server = getattr(error, 'isolated_server', None)
        raise
    owner.server.controller = PilotController(owner.runtime, envelope)
    owner.server.timeout = 0.2
