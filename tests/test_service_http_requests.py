"""Real bounded request threads retain unconfirmed sockets and startup ownership."""

import os
from threading import Event, Thread

import pytest

pytestmark = pytest.mark.skipif(os.name != 'nt', reason='native Windows runtime')

from tests.service_runtime_helpers import runtime_case, managed_process, wait_for
from tests.service_http_helpers import compose, dispatch, WireSocket, start_http


def test_sixteen_request_bound_and_unfinished_requests_fence_runtime_shutdown(runtime_case, tmp_path, monkeypatch):
    server, _ = compose(runtime_case, tmp_path)
    entered, release = Event(), Event()
    runtime_case.releases.append(release)
    calls = []
    def held(*_):
        calls.append(True)
        entered.set()
        assert release.wait(30)
    monkeypatch.setattr(server, 'finish_request', held)
    connections = [WireSocket(b'') for _ in range(17)]
    try:
        for connection in connections:
            server.process_request(connection, ('127.0.0.1', 1))
        assert entered.wait(10)
        wait_for(lambda: len(calls) == 16)
        assert len(server.requests.owners) == 16 and connections[-1].closed.is_set()
        result = server.shutdown_components()
        assert not result['complete'] and not result['requests_joined']
        assert not server.runtime.authority_closed and server.runtime.closed
        refused = WireSocket(b'')
        server.process_request(refused, ('127.0.0.1', 1))
        assert refused.closed.is_set() and len(calls) == 16
        release.set()
        assert server.shutdown_components()['complete']
        assert not server.requests.owners
    finally:
        release.set()
        server.server_close()


def test_request_socket_close_failure_stays_on_original_live_thread(runtime_case, tmp_path, monkeypatch):
    server, _ = compose(runtime_case, tmp_path)
    original = server.shutdown_request
    fail = [True]
    first = OSError('socket teardown secret')
    def close(request):
        if fail[0]:
            raise first
        original(request)
    monkeypatch.setattr(server, 'shutdown_request', close)
    try:
        dispatch(server, 'GET', '/health')
        wait_for(lambda: first in server.runtime.errors)
        assert not server.shutdown_components()['complete']
        assert server.requests.owners and not server.runtime.authority_closed
        fail[0] = False
        assert server.shutdown_components()['complete']
        assert not server.requests.owners
    finally:
        fail[0] = False
        server.server_close()


def test_known_request_prestart_failure_retires_socket_without_false_owner(runtime_case, tmp_path):
    first = OSError('native request thread was not started')
    class Unstarted(Thread):
        def start(self):
            raise first
    server, _ = compose(runtime_case, tmp_path, request_thread_factory=Unstarted)
    connection = WireSocket(b'')
    try:
        with pytest.raises(OSError) as failure:
            server.process_request(connection, ('127.0.0.1', 1))
        assert failure.value is first and connection.closed.is_set()
        assert not server.requests.owners
        assert server.shutdown_components()['complete']
    finally:
        server.server_close()


def test_incomplete_http_shutdown_still_requests_capture_stop(runtime_case, tmp_path, monkeypatch):
    ready, release = runtime_case.hold('live')
    runtime_case.cooperative.add('live')
    server, client = compose(runtime_case, tmp_path)
    fail = [True]
    original = server.shutdown_request
    def close(request):
        if fail[0]:
            raise OSError('request socket close unconfirmed')
        original(request)
    try:
        accepted = start_http(client, server.runtime, 'live')
        assert ready.wait(10)
        entry = server.runtime.captures[accepted['session_id']]
        monkeypatch.setattr(server, 'shutdown_request', close)
        dispatch(server, 'GET', '/health')
        assert not server.shutdown_components()['complete']
        assert entry['bridge'].stop_event.is_set()
        assert not server.runtime.authority_closed
        fail[0] = False
        release.set()
        assert server.shutdown_components()['complete']
    finally:
        fail[0] = False
        release.set()
        server.server_close()


def test_prestart_and_socket_close_failures_keep_primary_and_reachable_owner(runtime_case, tmp_path, monkeypatch):
    first, secondary = OSError('request never started'), OSError('socket close unconfirmed')
    class Unstarted(Thread):
        def start(self):
            raise first
    server, _ = compose(runtime_case, tmp_path, request_thread_factory=Unstarted)
    connection, original = WireSocket(b''), server.shutdown_request
    fail = [True]
    def close(request):
        if fail[0]:
            raise secondary
        original(request)
    monkeypatch.setattr(server, 'shutdown_request', close)
    try:
        with pytest.raises(OSError) as failure:
            server.process_request(connection, ('127.0.0.1', 1))
        assert failure.value is first
        assert first in server.runtime.errors and secondary in server.runtime.errors
        assert server.requests.owners and not connection.closed.is_set()
        assert not server.shutdown_components()['complete']
        assert not server.runtime.authority_closed
        fail[0] = False
        assert server.shutdown_components()['complete']
        assert connection.closed.is_set() and not server.requests.owners
    finally:
        fail[0] = False
        server.server_close()
