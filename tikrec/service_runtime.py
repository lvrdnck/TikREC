"""Explicit experimental composition; normal serve/CLI never constructs this backend."""

import time
from pathlib import Path
from threading import Event, RLock, Thread

from .capture_handoff_authority import CaptureAuthority
from .recording import RecordingBusy
from .service_runtime_capture import start_capture, callback, retain_thread_after_error
from .service_runtime_status import session_status, health, recordings, singular, stop
from .service_runtime_worker import processing_loop
from .service_runtime_shutdown import shutdown
from .service_runtime_automation import start_automatic, reconcile_claim
from .storage_status import StorageStatus
from .session_journal_types import require
from .service_runtime_connections import RuntimeConnections


class IsolatedServiceRuntime:
    """Own one identified schema-10 catalog, two captures and one FIFO worker.

    Initialize disposable catalogs separately with SessionJournal.initialize.
    Construction acquires catalog ownership before any worker/reconciliation.
    start_runtime is explicit. This backend is not wired into public HTTP/serve.
    Observation/worker factories are trusted offline integration seams, not API
    request fields. Existing media algorithms and native capability guards apply.
    """

    def __init__(self, journal, root, *, ffmpeg, ffprobe, storage_status=None,
                 observations=lambda bridge: {}, settlement_options=None,
                 thread_factory=Thread, shutdown_grace=30, poll_interval=0.2,
                 recovery_fault=lambda _: None, catalog_storage=None,
                 clock=time.time, notify=None):
        require(type(shutdown_grace) in {int, float} and 0 <= shutdown_grace <= 30)
        require(type(poll_interval) in {int, float} and 0 < poll_interval <= 1)
        require(all(callable(value) for value in (observations, thread_factory, clock, recovery_fault))
                and (notify is None or callable(notify)), 'trusted runtime hooks must be callable')
        self.root = Path(root).absolute()
        self.ffmpeg, self.ffprobe = Path(ffmpeg), Path(ffprobe)
        require(self.ffmpeg.is_absolute() and self.ffprobe.is_absolute(), 'media tools must be explicit absolute paths')
        self.observations, self.settlement_options = observations, dict(settlement_options or {})
        self.storage = storage_status or StorageStatus(self.root)
        require(Path(self.storage.output_directory).absolute() == self.root,
                'storage readiness must describe the explicit media root')
        self.catalog_storage = catalog_storage or StorageStatus(journal.path.parent,
            self.storage.minimum_free_bytes // (1024**3), disk_usage=self.storage._disk_usage)
        require(Path(self.catalog_storage.output_directory).absolute() == journal.path.parent,
                'catalog storage readiness must describe the explicit catalog root')
        self.authority = CaptureAuthority(journal, self.root)
        self.journal = journal
        self.thread_factory, self.clock = thread_factory, clock
        self.grace, self.poll_interval, self.notify = shutdown_grace, poll_interval, notify
        self.lock, self.wake, self.stopping = RLock(), Event(), Event()
        self.captures, self.latest, self.capture_errors = {}, {}, {}
        self.worker, self.current, self.recovery_address = None, None, None
        self.started, self.closed, self.authority_closed = False, False, False
        self.paused, self.errors, self.errors_dropped = None, [], 0
        self.cleanup_requested, self.shutdown_result = Event(), None
        self.automation = None
        self.recovery_fault = recovery_fault
        self.connections = RuntimeConnections(self.journal)
        self.connections.install()

    def start_runtime(self):
        """Explicitly launch the tracked reconciler; constructor/reopen remain passive."""
        with self.lock:
            require(not self.started and not self.closed, 'runtime start is single-use')
            self.started = True
            try:
                self.worker = self.thread_factory(target=processing_loop, args=(self,),
                                                  name='tikrec-isolated-finalizer', daemon=False)
                self.worker.start()
            except BaseException as error:
                self.record_error(error)
                self.paused, self.closed = 'worker_launch_failed', True
                self.stopping.set()
                self.wake.set()
                if not retain_thread_after_error(self, self.worker, error):
                    self.worker = None
                raise
        return self

    def storage_reason(self):
        """Apply the existing readiness/minimum-free barrier without reserving guessed bytes."""
        try:
            for storage in (self.storage, self.catalog_storage):
                value = storage.snapshot()
                if value['state'] not in {'ok', 'warning', 'blocked'} or value['free_bytes'] is None:
                    return 'storage_unavailable'
                if value['free_bytes'] < storage.minimum_free_bytes:
                    return 'low_free_space'
        except Exception:
            return 'storage_unavailable'
        return None

    def record_error(self, error):
        """Keep actual first/secondary errors bounded and separately report dropped errors."""
        with self.lock:
            if len(self.errors) < 32:
                self.errors.append(error)
            else:
                self.errors_dropped += 1

    def start(self, url, output, *, raw_copy=False, expected_room_id=None):
        """Accept durable capture before source opening; retain normal manual call shape."""
        return start_capture(self, url, output, raw_copy, expected_room_id)

    def start_automatic(self, claim, *, raw_copy=False):
        """Bind the persisted automatic claim to the journal acceptance transaction."""
        return start_automatic(self, claim, raw_copy)

    def reconcile_automatic_claim(self, claim):
        """Resolve acceptance through the indexed receipt even after H and slot reuse."""
        return reconcile_claim(self, claim)

    def prior_session_id_for_start(self):
        """Fingerprint the selected capture generation for the existing automation interface."""
        with self.lock:
            if self.closed or not self.started:
                raise RecordingBusy('service is not accepting starts')
            bindings = self.journal.status()['bindings']
            free = next((b for b in bindings if b['session'] is None), None)
            if free is None:
                raise RecordingBusy('recording capacity is unavailable')
            return self.latest.get(free['slot'])

    def capture_callback(self, session_id, generation, kind, *values):
        """Reject stale progress/state rather than mutating a replacement capture."""
        return callback(self, session_id, generation, kind, *values)

    def session_status(self, session_id):
        """Return stable addressed capture/finalization/completion facts."""
        return session_status(self, session_id)

    def health(self):
        """Separate capture availability from counted outstanding finalization."""
        return health(self)

    def recordings(self):
        """Project two capture slots plus bounded outstanding independent sessions."""
        return recordings(self)

    def jobs(self):
        """Expose bounded outstanding jobs for monitoring room suppression."""
        return tuple(self.session_status(unit['session']) for unit in self.journal.status()['units']) or ({'state': 'idle'},)

    def status(self):
        """Keep singular ambiguity explicit across capture and artifact ownership."""
        return singular(self)

    def stop(self, session_id=None):
        """Stop only the addressed current capture; closed capture is a no-op."""
        return stop(self, session_id)

    def shutdown(self):
        """Fence starts, seal captures, bound finalizer grace and retain uncertain authority."""
        return shutdown(self)
