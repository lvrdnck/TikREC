"""Real loopback acceptance reserves and the integrated runtime shutdown barrier."""

import os
from threading import Event, Thread

import pytest

pytestmark = pytest.mark.skipif(os.name != 'nt', reason='native Windows runtime')

from tests.service_runtime_helpers import runtime_case, managed_process, wait_for
from tests.service_http_accept_helpers import loopback
from tests.service_http_helpers import WireSocket


@pytest.mark.parametrize('gate', ['closed', 'capacity'])
def test_failed_refusal_consumes_bounded_reserve_and_pauses_native_accept(gate, runtime_case, tmp_path, monkeypatch):
    with loopback(runtime_case, tmp_path) as wire:
        server = wire.server
        monkeypatch.setattr(server, 'finish_request', wire.hold)
        if gate == 'capacity':
            for _ in range(16):
                wire.connect()
                assert wire.handle() is None
            wait_for(lambda: len(wire.calls) == 16)
        else:
            server.requests.closed = True
        fault = OSError('refused close still uncertain')
        wire.listener.next_error = fault
        wire.connect(request=False)
        assert wire.handle() is None
        refused = wire.accepted[-1]
        owners = tuple(server.requests.owners.values())
        assert len(owners) == (17 if gate == 'capacity' else 1)
        assert sum(o['kind'] == 'worker' for o in owners) == (16 if gate == 'capacity' else 0)
        for _ in range(3):
            wire.connect(request=False)
            assert wire.handle() is None
        assert len(wire.accepted) == len(owners) and refused.closes == ['MainThread']
        # Trusted direct calls cannot evade the budget; that caller keeps its socket.
        bypass = WireSocket(b'')
        with pytest.raises(RuntimeError, match='reserve unavailable'):
            server.process_request(bypass, ('127.0.0.1', 1))
        assert not bypass.closed.is_set()
        bypass.close()
        wire.release.set()
        wait_for(lambda: all(not o['thread'].is_alive() for o in owners if o['kind'] == 'worker'))
        assert not server.requests.join(5)
        assert len(server.requests.owners) == 1 and refused.fileno() >= 0
        assert wire.handle() is None and len(wire.accepted) == len(owners)
        refused.close_error = None
        assert server.requests.join(5, closing=True)
        # Explicitly repaired reserve allows a queued refusal to retire normally.
        assert wire.handle() is None and len(wire.accepted) == len(owners) + 1
        assert wire.accepted[-1].fileno() == -1
        assert server.shutdown_components()['complete']
        # An integrated shutdown fences native acceptance, even with queued clients.
        assert wire.handle() is None and len(wire.accepted) == len(owners) + 1


def test_registered_acceptance_in_flight_blocks_authority_release(runtime_case, tmp_path, monkeypatch):
    with loopback(runtime_case, tmp_path) as wire:
        entered, release = Event(), Event()
        runtime_case.releases.append(release)
        def verify(*_):
            entered.set()
            assert release.wait(30)
            return True
        monkeypatch.setattr(wire.server, 'verify_request', verify)
        wire.connect()
        errors = []
        accepter = Thread(target=lambda: errors.append(wire.handle()), name='in-flight-accept', daemon=False)
        accepter.start()
        try:
            assert entered.wait(10)
            owner = next(iter(wire.server.requests.owners.values()))
            assert owner['kind'] == 'accepted' and owner['thread'] is None
            result = wire.server.shutdown_components()
            assert not result['complete'] and not result['requests_joined']
            assert not wire.server.runtime.authority_closed
            assert wire.accepted[0].fileno() >= 0 and not wire.accepted[0].closes
        finally:
            release.set()
            accepter.join(5)
        assert not accepter.is_alive() and errors == [None]
        assert wire.accepted[0].closes == ['in-flight-accept']
        assert wire.server.shutdown_components()['complete']


def test_continuous_accept_loop_keeps_lost_ack_owner_and_fences_late_accepts(runtime_case, tmp_path, monkeypatch):
    first = OSError('continuous loop lost startup acknowledgement')
    class Partial(Thread):
        def start(self):
            super().start()
            raise first
    with loopback(runtime_case, tmp_path, request_thread_factory=Partial) as wire:
        monkeypatch.setattr(wire.server, 'finish_request', wire.hold)
        with wire.serving() as accepter:
            client = wire.connect()
            assert wire.entered.wait(10)
            # Handler entry precedes Thread.start returning on the accept thread.
            wait_for(lambda: first in wire.server.runtime.errors)
            assert first in wire.server.runtime.errors and accepter.is_alive()
            assert wire.accepted[0].fileno() >= 0 and not wire.accepted[0].closes
            assert not wire.server.shutdown_components()['complete']
            wire.connect(request=False)
            wire.release.set()
            assert b'HTTP/1.0 200' in wire.read(client)
            assert wire.server.shutdown_components()['complete']
            assert len(wire.accepted) == 1 and not wire.server.requests.owners
        assert not accepter.is_alive()
