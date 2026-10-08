"""Review probes for refusal ownership through continuous acceptance and shutdown."""

import os
from threading import Event

import pytest

from tests.service_runtime_helpers import runtime_case, managed_process, wait_for
from tests.service_http_accept_helpers import loopback

pytestmark = pytest.mark.skipif(os.name != 'nt', reason='native Windows runtime')


@pytest.mark.parametrize('gate', ['closed', 'capacity'])
def test_continuous_refusal_retains_reserve_after_listener_close(
        gate, runtime_case, tmp_path, monkeypatch):
    """A pending close pauses real accepts and outlives listener retirement."""
    with loopback(runtime_case, tmp_path) as wire:
        server = wire.server
        monkeypatch.setattr(server, 'finish_request', wire.hold)
        cycles, observed = [], Event()
        threshold = [None]

        def observe_cycle():
            cycles.append(None)
            if threshold[0] is not None and len(cycles) >= threshold[0]:
                observed.set()

        monkeypatch.setattr(server, 'service_actions', observe_cycle)
        with wire.serving() as accepter:
            if gate == 'capacity':
                for _ in range(16):
                    wire.connect()
                wait_for(lambda: len(wire.calls) == 16)
            else:
                server.requests.closed = True
            fault = OSError('review refusal close remains unconfirmed')
            wire.listener.next_error = fault
            wire.connect(request=False)
            wait_for(lambda: fault in server.runtime.errors)
            refused = wire.accepted[-1]
            owner = server.requests._find(refused)
            count = 17 if gate == 'capacity' else 1
            assert owner['kind'] == 'socket' and len(server.requests.owners) == count
            for _ in range(3):
                wire.connect(request=False)
            # Observe completed loop iterations with a ready backlog, not elapsed time.
            threshold[0] = len(cycles) + 3
            assert observed.wait(10) and accepter.is_alive()
            assert len(wire.accepted) == count
            assert refused.closes == ['disposable-http-accept']
            wire.release.set()
            wait_for(lambda: all(not o['thread'].is_alive()
                for o in tuple(server.requests.owners.values()) if o['kind'] == 'worker'))
            assert not server.requests.join(5)
            assert len(server.requests.owners) == 1 and server.requests._find(refused) is owner
            assert refused.fileno() >= 0 and refused.closes == ['disposable-http-accept']
            result = server.shutdown_components()
            assert not result['complete'] and not result['requests_joined']
            assert not server.runtime.authority_closed
        # The selector is joined before listener close; a closed listener is no proof
        # that its independently owned, failed-close connection has retired.
        server.server_close()
        assert server.socket.fileno() == -1 and refused.fileno() >= 0
        assert not server.shutdown_result['complete']
        assert server.requests._find(refused) is owner
        refused.close_error = None  # Fixture repair only; product must retry and prove close.
        result = server.shutdown_components()
        assert result['complete'] and server.runtime.authority_closed
        assert refused.fileno() == -1 and not server.requests.owners
