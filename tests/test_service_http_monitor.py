"""Original monitor thread ownership and automatic raw/acceptance identity over HTTP."""

import os
from pathlib import Path
from threading import Event, Thread, get_ident

import pytest

pytestmark = pytest.mark.skipif(os.name != 'nt', reason='native Windows runtime')

from tests.service_runtime_helpers import runtime_case, managed_process, wait_for
from tests.service_http_helpers import compose, start_http, client_for, TOKEN
from tests.test_service_http_lifecycle import components
from tests.manifest_fence_helpers import ConnectionFaults
from tikrec.service_http_runtime import IsolatedRecordingHTTPServer
from tikrec.automation import AutomationCoordinator
from tikrec.service_runtime_automation import claim_id


def test_monitor_sqlite_owner_remains_on_original_thread_until_cleanup(runtime_case, tmp_path, monkeypatch):
    values = components(runtime_case, tmp_path)
    runtime, monitor = values['runtime'], values['monitor']
    original, retained = runtime.connections.original, []
    first = OSError('monitor SQLite close signed://secret')
    def once():
        import threading
        connection = original()
        if threading.current_thread().name == 'tikrec-monitor' and not retained:
            connection = ConnectionFaults(connection, close=first)
            retained.append((get_ident(), connection))
        return connection
    monkeypatch.setattr(runtime.connections, 'original', once)
    # Exercise the real monitor Thread and its original shutdown path offline.
    monitor._creators = ('example.creator',)
    def run():
        runtime.health()
    monkeypatch.setattr(monitor, '_run', run)
    server = IsolatedRecordingHTTPServer(port=0, token=TOKEN, request_grace=0.1, **values)
    try:
        wait_for(lambda: runtime.connections.failed(runtime))
        assert retained[0][0] != get_ident() and server.monitor_owner.thread.is_alive()
        value = client_for(server).health()
        assert value['active_count'] is None and 'secret' not in str(value)
        assert not server.shutdown_components()['complete']
        assert not runtime.authority_closed
        retained[0][1].close_error = None
        assert server.shutdown_components()['complete']
        assert not server.monitor_owner.thread.is_alive()
        assert not runtime.connections.has_ownership()
    finally:
        if retained:
            retained[0][1].close_error = None
        server.server_close()


def test_monitor_native_start_ack_loss_keeps_exact_thread(runtime_case, tmp_path, monkeypatch):
    values = components(runtime_case, tmp_path)
    monitor = values['monitor']
    entered, release = Event(), Event()
    runtime_case.releases.append(release)
    first = OSError('monitor native launch acknowledgement lost')
    class Partial(Thread):
        def start(self):
            super().start()
            raise first
    monitor._creators = ('example.creator',)
    monitor._thread_factory = Partial
    monkeypatch.setattr(monitor, '_run', lambda: (entered.set(), release.wait(30)))
    try:
        with pytest.raises(OSError) as failure:
            IsolatedRecordingHTTPServer(port=0, request_grace=0.1, **values)
        assert failure.value is first and entered.wait(10)
        server = first.isolated_server
        assert monitor._thread is None  # Existing start dropped its acknowledgement reference.
        assert server.monitor_owner.thread.is_alive() and not first.isolated_shutdown['complete']
        assert not server.runtime.authority_closed
        release.set()
        assert server.shutdown_components()['complete']
    finally:
        release.set()


@pytest.mark.parametrize('raw', [False, True])
def test_automatic_acceptance_ack_loss_keeps_raw_original_uuid_across_http_slot_reuse(runtime_case, tmp_path, raw):
    case = runtime_case
    entered, release = Event(), Event()
    case.releases.append(release)
    def fault(point):
        if point == 'after_media_plan':
            entered.set()
            assert release.wait(60)
    case.fault = fault
    class Partial(Thread):
        def start(self):
            super().start()
            raise OSError('automatic capture launch acknowledgement lost')
    def factory(**options):
        return Partial(**options) if options['name'].startswith('tikrec-isolated-capture') else Thread(**options)
    runtime = case.build(thread_factory=factory)
    server, client = compose(case, tmp_path, runtime=runtime,
        raw_creators=('example.creator',) if raw else ())
    cycle = {'cycle_count': 1, 'creators': [{'creator': 'example.creator', 'state': 'live', 'room_id': '123'}]}
    try:
        server.automation.cycle_completed(cycle)
        claim = server.automation._store.load().pending_claim
        assert claim is not None and entered.wait(30)
        sid = runtime.journal.automatic_receipt(claim_id(claim))['session']
        original = client.status(sid)
        assert original['raw_copy_enabled'] is raw and original['room_id'] == '123'
        runtime.thread_factory = Thread
        for index in range(2):
            name = 'replacement-' + str(index)
            ready, done = case.hold(name)
            item = start_http(client, runtime, name, creator='example.reuse' + str(index), raw=not raw)
            assert ready.wait(10)
            assert item['session_id'] != sid and item['raw_copy_enabled'] is not raw
        assert client.status(sid)['origin_slot_id'] == original['origin_slot_id']
        assert client.status(sid)['raw_copy_enabled'] is raw
        assert client.stop(sid)['stop_result'] == 'capture_already_closed'
        # Reconcile from the durable claim with the opposite *new* raw preference.
        reconciled = AutomationCoordinator(runtime, server.admission, server.automation._store,
            automatic_raw_copy_creators=() if raw else ('example.creator',))
        assert reconciled._store.load().pending_claim is None
        assert reconciled._store.load().consumed()['example.creator'] == '123'
        assert runtime.reconcile_automatic_claim(claim)
        assert client.status(sid)['raw_copy_enabled'] is raw
        # Monitoring transport still reports the original coordinator's fixed blocked fact.
        assert client.monitoring()['automation']['blocked_reason'] == 'automation_state_ambiguous'
    finally:
        release.set()
        for _, done in case.holds.values():
            done.set()
        server.server_close()
