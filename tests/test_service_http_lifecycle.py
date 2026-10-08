"""Isolated composition rejects parallel authority and preserves startup/shutdown owners."""

import os
import socket
from threading import Event, Thread

import pytest

pytestmark = pytest.mark.skipif(os.name != 'nt', reason='native Windows runtime')

from tests.service_runtime_helpers import runtime_case, managed_process, wait_for
from tests.service_http_helpers import compose, dispatch, response, WireSocket, TOKEN
from tikrec.admission import RecordingAdmission
from tikrec.automation import AutomationCoordinator
from tikrec.automation_state import AutomationStateStore
from tikrec.monitoring import CreatorMonitor
from tikrec.service_http_runtime import IsolatedRecordingHTTPServer


def components(case, tmp_path, runtime=None):
    """Construct passive isolated components using only supplied disposable state."""
    runtime = runtime or case.build(shutdown_grace=0)
    admission = RecordingAdmission(runtime.root, runtime.health, storage_status=runtime.storage)
    automation = AutomationCoordinator(runtime, admission, AutomationStateStore(tmp_path / 'isolated.json'))
    monitor = CreatorMonitor((), cycle_completed=automation.cycle_completed)
    return dict(runtime=runtime, admission=admission, automation=automation, monitor=monitor)


@pytest.mark.parametrize('conflict', ['controller', 'manager', 'automation_store', 'output_directory', 'bind_and_activate'])
def test_conflicting_legacy_arguments_rejected_before_listener_or_work(runtime_case, tmp_path, monkeypatch, conflict):
    values = components(runtime_case, tmp_path)
    import tikrec.service as legacy
    monkeypatch.setattr(legacy, 'default_job_state_path', lambda: pytest.fail('legacy path accessed'))
    monkeypatch.setattr(legacy, 'RecordingController', lambda **_: pytest.fail('parallel authority created'))
    with pytest.raises(ValueError, match='arguments conflict'):
        IsolatedRecordingHTTPServer(port=0, **values, **{conflict: object()})
    assert not values['runtime'].started and values['runtime'].worker is None
    assert not values['runtime'].journal.history()
    assert not values['monitor'].snapshot()['running']


def test_listener_reserved_before_runtime_or_monitor_starts(runtime_case, tmp_path, monkeypatch):
    values = components(runtime_case, tmp_path)
    runtime = values['runtime']
    with socket.socket() as held:
        held.bind(('127.0.0.1', 0))
        held.listen()
        with pytest.raises(OSError) as failure:
            IsolatedRecordingHTTPServer(port=held.getsockname()[1], **values)
        assert not runtime.started and runtime.worker is None
        assert failure.value.isolated_server.shutdown_result['complete']
        assert not values['monitor'].snapshot()['running']
    assert not runtime.journal.history()


def test_monitor_start_failure_preserves_primary_error_and_runtime_shutdown(runtime_case, tmp_path, monkeypatch):
    values = components(runtime_case, tmp_path)
    first = OSError('monitor startup secret')
    def failed():
        assert values['runtime'].started
        raise first
    monkeypatch.setattr(values['monitor'], 'start', failed)
    with pytest.raises(OSError) as failure:
        IsolatedRecordingHTTPServer(port=0, **values)
    assert failure.value is first and first.isolated_shutdown['complete']
    assert not values['runtime'].worker.is_alive()
    assert values['runtime'].authority_closed


def test_started_runtime_start_ack_loss_is_reported_incomplete(runtime_case, tmp_path):
    case = runtime_case
    entered, release = Event(), Event()
    case.releases.append(release)
    first = OSError('runtime launch acknowledgement secret')
    class Partial(Thread):
        def start(self):
            super().start()
            raise first
    def factory(**options):
        target, args = options['target'], options['args']
        def held():
            entered.set()
            assert release.wait(30)
            target(*args)
        return Partial(target=held, name=options['name'], daemon=False)
    values = components(case, tmp_path, case.build(thread_factory=factory, shutdown_grace=0))
    try:
        with pytest.raises(OSError) as failure:
            IsolatedRecordingHTTPServer(port=0, **values, request_grace=0)
        assert failure.value is first and entered.wait(10)
        server = first.isolated_server
        assert not first.isolated_shutdown['complete']
        assert not server.runtime.authority_closed and server.runtime.worker.is_alive()
        release.set()
        assert server.shutdown_components()['complete']
    finally:
        release.set()


def test_request_started_ack_loss_and_prestart_failure_remain_distinct(runtime_case, tmp_path):
    first = OSError('request launch acknowledgement secret')
    class Partial(Thread):
        def start(self):
            super().start()
            raise first
    server, _ = compose(runtime_case, tmp_path, request_thread_factory=Partial)
    connection = WireSocket(b'GET /health HTTP/1.1\r\nHost: localhost\r\nAuthorization: Bearer ' + TOKEN.encode() + b'\r\n\r\n')
    try:
        with pytest.raises(OSError) as failure:
            server.process_request(connection, ('127.0.0.1', 1))
        assert failure.value is first
        assert connection.sent.wait(10)
        assert response(connection)[0] == 200
        assert server.shutdown_components()['complete']
        assert not server.requests.owners
    finally:
        server.server_close()


def test_monitor_join_failure_and_listener_close_cannot_claim_safe_exit(runtime_case, tmp_path, monkeypatch):
    server, _ = compose(runtime_case, tmp_path)
    join = server.monitor.join
    first = OSError('monitor join secret')
    monkeypatch.setattr(server.monitor, 'join', lambda: (_ for _ in ()).throw(first))
    try:
        server.server_close()
        assert server.socket.fileno() == -1
        assert not server.shutdown_result['complete']
        assert server.shutdown_result['reason'] == 'monitor_cleanup_needs_attention'
        assert not server.runtime.authority_closed and first in server.runtime.errors
        monkeypatch.setattr(server.monitor, 'join', join)
        assert server.shutdown_components()['complete']
    finally:
        monkeypatch.setattr(server.monitor, 'join', join)
        server.server_close()


def test_listener_close_failure_keeps_socket_and_incomplete_transport_result(runtime_case, tmp_path, monkeypatch):
    server, _ = compose(runtime_case, tmp_path)
    held = server.socket
    first = OSError('listener close unconfirmed secret')
    class FaultSocket:
        def close(self):
            raise first
        def fileno(self):
            return held.fileno()
    # Native socket methods are read-only; retain the exact real listener beneath the fault.
    faulty = FaultSocket()
    server.socket = faulty
    try:
        with pytest.raises(OSError) as failure:
            server.server_close()
        assert failure.value is first and server.socket is faulty and held.fileno() >= 0
        assert not server.shutdown_result['complete']
        assert server.shutdown_result['reason'] == 'listener_cleanup_needs_attention'
        assert server.runtime.authority_closed  # Runtime retirement is a separate confirmed fact.
        assert not server.shutdown_components()['complete']
        server.socket = held
        assert server.server_close()['complete']
        assert held.fileno() == -1
    finally:
        server.socket = held
        server.server_close()
