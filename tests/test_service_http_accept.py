"""R16/R17 regressions through actual Windows loopback stdlib acceptance."""

import json
import os
from threading import Thread

import pytest

pytestmark = pytest.mark.skipif(os.name != 'nt', reason='native Windows runtime')

from tests.service_runtime_helpers import runtime_case, managed_process, wait_for
from tests.service_http_accept_helpers import loopback


@pytest.mark.parametrize('lost_ack', [False, True])
def test_accept_loop_keeps_started_request_socket_until_original_worker(lost_ack, runtime_case, tmp_path, monkeypatch):
    first = OSError('request startup acknowledgement lost')
    class Partial(Thread):
        def start(self):
            super().start()
            raise first
    with loopback(runtime_case, tmp_path, request_thread_factory=Partial if lost_ack else Thread) as wire:
        server = wire.server
        monkeypatch.setattr(server, 'finish_request', wire.hold)
        client = wire.connect()
        assert wire.handle() is None
        assert wire.entered.wait(10)
        accepted = wire.accepted[0]
        owner = next(iter(server.requests.owners.values()))
        print(json.dumps({'case': 'R16', 'lost_ack': lost_ack,
            'worker_alive': owner['thread'].is_alive(), 'socket_fd': accepted.fileno(),
            'close_threads_before_release': accepted.closes,
            'primary_recorded': first in server.runtime.errors}))
        assert owner['thread'].is_alive() and accepted.fileno() >= 0
        assert not accepted.closes
        if lost_ack:
            assert server.runtime.errors[0] is first
        assert not server.shutdown_components()['complete']
        assert not server.runtime.authority_closed and accepted.fileno() >= 0
        wire.release.set()
        assert b'HTTP/1.0 200' in wire.read(client)
        assert server.requests.join(5, closing=True)
        assert accepted.closes == ['tikrec-isolated-http'] and accepted.fileno() == -1
        assert server.shutdown_components()['complete']


@pytest.mark.parametrize('gate', ['closed', 'capacity'])
@pytest.mark.parametrize('failed_close', [False, True])
def test_accept_loop_refused_socket_remains_owned_until_confirmed_close(gate, failed_close, runtime_case, tmp_path, monkeypatch):
    with loopback(runtime_case, tmp_path) as wire:
        server = wire.server
        monkeypatch.setattr(server, 'finish_request', wire.hold)
        if gate == 'closed':
            server.requests.closed = True
        else:
            for _ in range(16):
                wire.connect()
                assert wire.handle() is None
            wait_for(lambda: len(wire.calls) == 16)
            assert len(server.requests.owners) == 16
        first = OSError('refused socket close unconfirmed')
        wire.listener.next_error = first if failed_close else None
        wire.connect(request=False)
        error = wire.handle()
        refused = wire.accepted[-1]
        assert refused.closes == ['MainThread']
        retained = next((o for o in server.requests.owners.values()
                         if o['request'] is refused), None)
        if failed_close:
            assert retained is not None and retained['kind'] == 'socket'
        wire.release.set()
        joined = server.requests.join(5, closing=True)
        result = server.shutdown_components()
        print(json.dumps({'case': 'R17', 'gate': gate, 'failed_close': failed_close,
            'error_escaped': error is not None, 'refused_socket_fd': refused.fileno(),
            'close_threads': refused.closes, 'owners': len(server.requests.owners),
            'joined': joined, 'complete': result['complete'],
            'authority_released': server.runtime.authority_closed,
            'primary_recorded': first in server.runtime.errors}))
        if failed_close:
            assert not joined and not result['complete']
            assert not server.runtime.authority_closed and refused.fileno() >= 0
            assert first in server.runtime.errors and server.requests.owners
            assert error is None
            # Two explicit failed retries must preserve the same socket and owner.
            assert not server.shutdown_components()['complete']
            assert server.requests.owners[id(retained)] is retained
            refused.close_error = None
            assert server.shutdown_components()['complete']
        else:
            assert joined and result['complete'] and error is None
        assert refused.fileno() == -1 and not server.requests.owners
