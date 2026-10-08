"""Explicit experimental HTTP composition; normal serve/configuration stays legacy."""

import json
import socket
from http.server import ThreadingHTTPServer
from threading import Thread

from .service import DEFAULT_HOST, DEFAULT_PORT, RecordingHandler
from .service_bind import validate_bind
from .service_http_monitoring import monitoring_projection
from .service_http_projection import RuntimeHTTPController, number
from .service_http_requests import RequestOwners
from .service_http_monitor import MonitorOwner
from .session_journal_types import identifier, require
from .recording_manager import RecordingNotFound


class IsolatedRecordingHandler(RecordingHandler):
    """Reuse existing auth/request protections with isolated projections and UUID lookup."""

    def do_GET(self):
        """Authenticate stable UUID/monitor lookup and sanitize unexpected backend errors."""
        try:
            if self.path.startswith('/sessions/'):
                if not self._authorized():
                    return
                sid = self.path[len('/sessions/'):]
                try:
                    identifier(sid)
                except ValueError:
                    self._json(400, {'error': 'session_id must be a canonical UUID'})
                    return
                try:
                    self._json(200, self.server.controller.session_status(sid))
                except RecordingNotFound:
                    self._json(404, {'error': 'recording session not found'})
            elif self.path == '/health':
                if self._authorized():
                    storage = self.server.storage_status.snapshot()
                    state = storage.get('state')
                    require(state in {'unconfigured', 'unavailable', 'ok', 'warning', 'blocked'})
                    self._json(200, {**self.server.controller.health(), 'storage':
                        {'state': state, **{key: number(storage.get(key)) for key in
                            ('free_bytes', 'minimum_free_bytes', 'warning_free_bytes')}}})
            elif self.path == '/monitoring':
                if self._authorized():
                    self._json(200, monitoring_projection(self.server))
            else:
                super().do_GET()
        except (BrokenPipeError, ConnectionResetError):
            raise
        except Exception as error:
            self.server.runtime.record_error(error)
            self._json(500, {'error': 'service status unavailable'})

    def do_POST(self):
        """Keep ordinary request fields/error categories and fixed unexpected failures."""
        try:
            super().do_POST()
        except (BrokenPipeError, ConnectionResetError):
            raise
        except Exception as error:
            self.server.runtime.record_error(error)
            self._json(500, {'error': 'service control unavailable'})

    def _json(self, status, value):
        encoded = json.dumps(value, allow_nan=False).encode('utf-8')
        if len(encoded) > 65536:
            status, value = 500, {'error': 'service response exceeds transport bound'}
        super()._json(status, value)


class IsolatedRecordingHTTPServer(ThreadingHTTPServer):
    """Own HTTP over one explicit runtime and explicitly composed isolated policy state.

    The caller constructs the identified runtime/admission/automation/monitor.
    This constructor never initializes a catalog, legacy controller or job store.
    Listener closure is separate from confirmed runtime/request retirement.
    """

    # ThreadingMixIn's unbounded server_close join would conceal incomplete shutdown.
    block_on_close = False

    def __init__(self, host=DEFAULT_HOST, port=DEFAULT_PORT, *, runtime, admission,
                 automation, monitor, token=None, request_grace=10,
                 request_thread_factory=Thread, **legacy_arguments):
        require(not legacy_arguments, 'isolated and legacy backend arguments conflict')
        require(not runtime.started and not runtime.closed, 'runtime must be passive')
        require(automation._controller is runtime and automation._admission is admission,
                'isolated automation must use the supplied runtime/admission')
        require(admission._controller_health == runtime.health
                and admission.storage_status is runtime.storage,
                'isolated admission must use supplied runtime/storage')
        require(monitor._cycle_completed == automation.cycle_completed,
                'isolated monitor must use supplied automation')
        require(monitor._thread is None and runtime.automation in {None, automation},
                'isolated components must be passive and share one automation owner')
        require(type(request_grace) in {int, float} and 0 <= request_grace <= 10)
        require(type(port) is int and 0 <= port <= 65535)
        host = validate_bind(host, token)
        self.address_family = socket.AF_INET6 if ':' in host else socket.AF_INET
        self.runtime, self.token = runtime, token
        self.admission, self.automation, self.monitor = admission, automation, monitor
        self.controller, self.storage_status = RuntimeHTTPController(runtime), runtime.storage
        self.request_grace, self.shutdown_result = request_grace, None
        self.listener_uncertain = False
        self.requests = RequestOwners(self, request_thread_factory)
        self.monitor_owner = MonitorOwner(self)
        # Reserve/bind before starting finalization or a monitor callback.
        try:
            super().__init__((host, port), IsolatedRecordingHandler)
            runtime.automation = automation
            runtime.start_runtime()
            self.monitor_owner.start()
        except BaseException as error:
            runtime.record_error(error)
            try:
                self.server_close()
            except BaseException as secondary:
                runtime.record_error(secondary)
            result = self.shutdown_result
            # Preserve the exact primary error and reachable incomplete owners.
            error.isolated_server, error.isolated_shutdown = self, result
            raise

    def process_request(self, request, client_address):
        """Bound tracked request concurrency and preserve ambiguous thread startup."""
        self.requests.start(request, client_address)

    def get_request(self):
        """Transfer a real accepted socket into the bounded registry immediately."""
        return self.requests.accept(super().get_request)

    def _handle_request_noblock(self):
        # BaseServer's fallback closes sockets after process_request raises, even
        # when native Thread.start succeeded. The isolated owner alone may close.
        if not self.requests.wait_capacity():
            return
        try:
            request, address = self.get_request()
        except OSError:
            return
        self.requests.handle_accepted(request, address)

    def handle_error(self, request, client_address):
        """Never print arbitrary backend exception text to HTTP-server stderr."""

    def shutdown_components(self):
        """Fence callbacks, retire request borrowers, then ask the sole runtime to close."""
        runtime = self.runtime
        self.requests.stop_accepting()
        with runtime.lock:
            runtime.closed = True
            runtime.stopping.set()
            runtime.wake.set()
            captures = tuple(sid for sid, entry in runtime.captures.items() if not entry['done'])
        # Request/monitor uncertainty cannot delay cooperative stop of accepted captures.
        # Use the original UUID authority fence; never signal a reused slot by index.
        for sid in captures:
            try:
                runtime.stop(sid)
            except RecordingNotFound:
                pass  # The same capture may have committed H/terminal success meanwhile.
            except BaseException as error:
                runtime.record_error(error)
        failed = False
        for action in (self.automation.stop, self.monitor.stop):
            try:
                action()
            except BaseException as error:
                runtime.record_error(error)
                failed = True
        failed = not self.monitor_owner.join(self.request_grace) or failed
        joined = self.requests.join(self.request_grace, closing=True)
        if joined and not failed:
            try:
                result = runtime.shutdown()
            except BaseException as error:
                runtime.record_error(error)
                result = None
        else:
            # Keep authority held while request/monitor ownership is uncertain.
            result = None
        self.shutdown_result = result or {'complete': False, 'captures_joined': False,
            'finalizer_joined': False, 'authority_released': False,
            'reason': 'monitor_cleanup_needs_attention' if failed else
                'request_threads_unconfirmed' if not joined else 'ownership_or_cleanup_unconfirmed',
            'diagnostic_count': len(runtime.errors), 'diagnostics_dropped': runtime.errors_dropped}
        self.shutdown_result = {**self.shutdown_result, 'requests_joined': joined, 'monitor_joined': not failed}
        if self.listener_uncertain:
            self.shutdown_result = {**self.shutdown_result, 'complete': False,
                'reason': 'listener_cleanup_needs_attention'}
        return self.shutdown_result

    def server_close(self):
        """Close only the listener; retain and report every incomplete component owner."""
        try:
            super().server_close()
            self.listener_uncertain = False
        except BaseException as error:
            self.listener_uncertain = True
            self.runtime.record_error(error)
            raise
        finally:
            if hasattr(self, 'requests'):
                self.shutdown_components()
        return self.shutdown_result
