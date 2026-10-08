"""Original-thread SQLite/socket retirement and primary failure precedence on TCP."""

import os
from threading import Thread, current_thread, get_ident

import pytest

pytestmark = pytest.mark.skipif(os.name != 'nt', reason='native Windows runtime')

from tests.service_runtime_helpers import runtime_case, managed_process, wait_for
from tests.service_http_accept_helpers import loopback
from tests.service_http_helpers import client_for, start_http
from tests.manifest_fence_helpers import ConnectionFaults


@pytest.mark.parametrize('native_started', [False, True])
def test_interrupted_unconfirmed_start_never_allows_foreign_socket_cleanup(native_started, runtime_case, tmp_path, monkeypatch):
    first = KeyboardInterrupt('startup interrupted before acknowledgement')
    class Unconfirmed(Thread):
        def start(self):
            if native_started:
                super().start()
            raise first
    with loopback(runtime_case, tmp_path, request_thread_factory=Unconfirmed) as wire:
        monkeypatch.setattr(wire.server, 'finish_request', wire.hold)
        client = wire.connect()
        assert wire.handle() is first
        owner = next(iter(wire.server.requests.owners.values()))
        worker = owner['thread']
        try:
            assert owner['kind'] == 'worker' and wire.server.runtime.errors[0] is first
            assert not wire.server.shutdown_components()['complete']
            assert not wire.server.runtime.authority_closed
            assert wire.accepted[0].fileno() >= 0 and not wire.accepted[0].closes
        finally:
            # Independent fixture repair makes deferred native startup observable;
            # a never-acknowledged object alone cannot establish safe product exit.
            if worker.ident is None:
                Thread.start(worker)
            wire.release.set()
        assert b'HTTP/1.0 200' in wire.read(client)
        assert wire.server.shutdown_components()['complete']
        assert not worker.is_alive() and wire.accepted[0].fileno() == -1
        assert wire.accepted[0].closes == ['tikrec-isolated-http']


@pytest.mark.parametrize('failed_close', [False, True])
def test_real_accept_known_prestart_preserves_primary_and_socket_owner(failed_close, runtime_case, tmp_path):
    first, secondary = OSError('request known not started'), OSError('prestart socket close failed')
    class Unstarted(Thread):
        def start(self):
            raise first
    with loopback(runtime_case, tmp_path, request_thread_factory=Unstarted) as wire:
        wire.listener.next_error = secondary if failed_close else None
        wire.connect()
        assert wire.handle() is None
        accepted = wire.accepted[0]
        assert accepted.closes == ['MainThread']
        assert wire.server.runtime.errors[0] is first
        if failed_close:
            assert wire.server.runtime.errors[1] is secondary
            assert not wire.server.shutdown_components()['complete']
            assert not wire.server.shutdown_components()['complete']
            assert accepted.fileno() >= 0 and not wire.server.runtime.authority_closed
            accepted.close_error = None
        assert wire.server.shutdown_components()['complete']
        assert accepted.fileno() == -1 and not wire.server.requests.owners


@pytest.mark.parametrize('verify_error', [False, True])
@pytest.mark.parametrize('failed_close', [False, True])
def test_verification_refusal_transfers_to_tracked_socket_cleanup(verify_error, failed_close, runtime_case, tmp_path, monkeypatch):
    first, secondary = OSError('verification failed'), OSError('verification refusal close failed')
    with loopback(runtime_case, tmp_path) as wire:
        def verify(*_):
            if verify_error:
                raise first
            return False
        monkeypatch.setattr(wire.server, 'verify_request', verify)
        wire.listener.next_error = secondary if failed_close else None
        wire.connect()
        assert wire.handle() is None
        accepted = wire.accepted[0]
        assert accepted.closes == ['MainThread']
        if verify_error:
            assert wire.server.runtime.errors[0] is first
        if failed_close:
            assert secondary in wire.server.runtime.errors
            assert not wire.server.shutdown_components()['complete']
            assert not wire.server.runtime.authority_closed
            accepted.close_error = None
        assert wire.server.shutdown_components()['complete']
        assert accepted.fileno() == -1 and not wire.server.requests.owners


def test_real_started_ack_loss_retains_secondary_socket_and_sqlite_on_original_thread(runtime_case, tmp_path, monkeypatch):
    first = OSError('original start acknowledgement lost')
    socket_error, sqlite_error = OSError('socket close failed'), OSError('SQLite close failed')
    class Partial(Thread):
        def start(self):
            super().start()
            raise first
    with loopback(runtime_case, tmp_path, request_thread_factory=Partial) as wire:
        runtime = wire.server.runtime
        original, retained, close_threads = runtime.connections.original, [], []
        class ObservedConnection(ConnectionFaults):
            def close(self):
                close_threads.append(get_ident())
                super().close()
        def connect():
            native = original()
            if current_thread().name == 'tikrec-isolated-http' and not retained:
                native = ObservedConnection(native, close=sqlite_error)
                retained.append((get_ident(), native))
            return native
        monkeypatch.setattr(runtime.connections, 'original', connect)
        monkeypatch.setattr(wire.server, 'finish_request', wire.hold)
        wire.listener.next_error = socket_error
        client = wire.connect()
        assert wire.handle() is None and wire.entered.wait(10)
        owner = next(iter(wire.server.requests.owners.values()))
        assert runtime.errors[0] is first and not wire.accepted[0].closes
        wire.release.set()
        assert b'HTTP/1.0 200' in wire.read(client)
        wait_for(lambda: socket_error in runtime.errors and sqlite_error in runtime.errors)
        for _ in range(2):
            assert not wire.server.shutdown_components()['complete']
            assert owner['thread'].is_alive() and wire.server.requests.owners[id(owner)] is owner
        assert not runtime.authority_closed and runtime.connections.has_ownership()
        assert wire.accepted[0].fileno() >= 0
        retained[0][1].close_error = None
        wire.accepted[0].close_error = None
        assert wire.server.shutdown_components()['complete']
        assert close_threads and set(close_threads) == {retained[0][0]}
        assert retained[0][0] != get_ident()
        assert set(wire.accepted[0].closes) == {'tikrec-isolated-http'}
        assert wire.accepted[0].fileno() == -1 and not owner['thread'].is_alive()
        assert not runtime.connections.has_ownership() and not wire.server.requests.owners
        assert runtime.errors[0] is first


def test_failed_refusal_shutdown_stops_original_capture_before_http_retry(runtime_case, tmp_path):
    ready, release = runtime_case.hold('live')
    runtime_case.cooperative.add('live')
    with loopback(runtime_case, tmp_path) as wire:
        server = wire.server
        accepted = start_http(client_for(server), server.runtime, 'live')
        assert ready.wait(10)
        entry = server.runtime.captures[accepted['session_id']]
        assert server.requests.join(5)
        server.requests.closed = True
        wire.listener.next_error = OSError('refused socket close unconfirmed')
        wire.connect(request=False)
        assert wire.handle() is None
        refused = wire.accepted[0]
        try:
            assert not server.shutdown_components()['complete']
            assert entry['bridge'].stop_event.is_set() and not server.runtime.authority_closed
        finally:
            release.set()
        refused.close_error = None
        # Cooperative stop requests precede asynchronous H/SQLite retirement.
        # Wait for the exact capture, then explicitly retry the bounded barrier.
        entry['thread'].join(10)
        assert not entry['thread'].is_alive()
        result = server.shutdown_components()
        assert result['complete'], result
        assert refused.fileno() == -1
