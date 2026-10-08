"""Connected storage/catalog/output, acknowledgement, malformed-input and cleanup faults."""

import os
from pathlib import Path
from threading import Event, Thread, get_ident

import pytest

pytestmark = pytest.mark.skipif(os.name != 'nt', reason='native Windows runtime')

from tests.service_runtime_helpers import runtime_case, managed_process, wait_for
from tests.service_http_helpers import compose, start_http, dispatch, response, TOKEN
from tests.manifest_fence_helpers import ConnectionFaults
from tikrec.remote import RemoteError


@pytest.mark.parametrize('route', ['/health', '/recording', '/recordings', '/monitoring',
    '/sessions/00000000-0000-0000-0000-000000000123'])
def test_auth_origin_malformed_uuid_and_no_internals(runtime_case, tmp_path, route):
    server, client = compose(runtime_case, tmp_path)
    try:
        assert response(dispatch(server, 'GET', route, headers={'Authorization': 'bad'}))[0] == 401
        assert response(dispatch(server, 'GET', route, headers={'Origin': 'https://evil.test'}))[0] == 403
        assert response(dispatch(server, 'GET', '/sessions/bad'))[0] == 400
        assert response(dispatch(server, 'GET', '/sessions/00000000-0000-0000-0000-000000000123'))[0] == 404
        assert response(dispatch(server, 'POST', '/recording/stop', {'session_id': 'bad'}))[0] == 400
        assert response(dispatch(server, 'POST', '/recording/start', {'url': 'signed', 'output': 'bad', 'expected_room_id': '123'}))[0] == 400
        health = client.health()
        assert health['capabilities'] == ['durable_finalization_v1']
        assert 'secret' not in str(health) and 'sqlite' not in str(health)
        assert str(server.runtime.journal.path) not in str(health)
        assert client.monitoring()['creators'] == []
    finally:
        server.server_close()


@pytest.mark.parametrize('disconnect', [False, True])
def test_request_close_failure_retains_original_thread_and_incomplete_shutdown(runtime_case, tmp_path, monkeypatch, disconnect):
    server, client = compose(runtime_case, tmp_path)
    runtime = server.runtime
    original, retained = runtime.connections.original, []
    first = OSError('private SQLite capability signed://secret')
    caller = get_ident()
    def once():
        connection = original()
        import threading
        if threading.current_thread().name == 'tikrec-isolated-http' and not retained:
            connection = ConnectionFaults(connection, close=first)
            retained.append((get_ident(), connection))
        return connection
    monkeypatch.setattr(runtime.connections, 'original', once)
    try:
        connection = dispatch(server, 'GET', '/health', disconnect=disconnect)
        wait_for(lambda: runtime.connections.failed(runtime))
        if not disconnect:
            code, value = response(connection)
            assert code == 200 and value['active_count'] is None
            assert value['finalization']['outstanding_units'] is None
            assert 'secret' not in str(value)
        assert connection.closed.wait(10)
        assert retained[0][0] != caller and runtime.errors[0] is first
        assert server.requests.owners
        result = server.shutdown_components()
        assert not result['complete'] and not result['authority_released']
        assert not runtime.authority_closed and runtime.connections.has_ownership()
        # Independent repair removes only the injected close fault, not the owner.
        retained[0][1].close_error = None
        assert server.shutdown_components()['complete']
        assert not server.requests.owners and not runtime.connections.has_ownership()
    finally:
        if retained:
            retained[0][1].close_error = None
        server.server_close()


def test_lost_http_acknowledgement_preserves_one_addressable_capture(runtime_case, tmp_path):
    case = runtime_case
    entered, release = case.hold('lost')
    case.cooperative.add('lost')
    server, client = compose(case, tmp_path)
    runtime = server.runtime
    try:
        dispatch(server, 'POST', '/recording/start', {'url': 'https://www.tiktok.com/@example.creator/live',
            'output': str(runtime.root / 'lost.mp4'), 'raw_copy': True}, disconnect=True)
        assert entered.wait(10)
        sid = runtime.latest[1]
        assert client.status(sid)['active'] and client.status(sid)['raw_copy_enabled']
        assert len(runtime.journal.history()) == 1
        assert client.stop(sid)['stop_requested']
        release.set()
        wait_for(lambda: runtime.session_status(sid)['output_completed'])
        assert len(runtime.journal.history()) == 1
        assert server.shutdown_components()['complete']
    finally:
        release.set()
        server.server_close()


@pytest.mark.parametrize('storage', ['output', 'catalog'])
def test_storage_refusal_is_fixed_and_physical_slots_stay_free(runtime_case, tmp_path, monkeypatch, storage):
    server, client = compose(runtime_case, tmp_path)
    runtime = server.runtime
    status = runtime.storage if storage == 'output' else runtime.catalog_storage
    original = status._disk_usage
    monkeypatch.setattr(status, '_disk_usage', lambda _: (_ for _ in ()).throw(OSError('signed://secret')))
    try:
        health = client.health()
        assert health['available_slots'] == 2 and not health['admission_available']
        assert health['admission_reason'] == 'storage_unavailable'
        with pytest.raises(RemoteError, match='HTTP 409'):
            start_http(client, runtime, 'refused')
        assert not runtime.journal.history()
        monkeypatch.setattr(status, '_disk_usage', original)
        assert client.health()['admission_available']
    finally:
        server.server_close()


def test_published_output_and_terminal_reporting_have_distinct_truth(runtime_case, tmp_path):
    case = runtime_case
    entered, release = Event(), Event()
    case.releases.append(release)
    def fault(point):
        if point == 'before_release_preparation':
            entered.set()
            assert release.wait(45)
        if point == 'after_terminal_release':
            raise OSError('local reporting signed://secret')
    case.fault = fault
    server, client = compose(case, tmp_path)
    runtime = server.runtime
    try:
        accepted = start_http(client, runtime, 'published')
        sid = accepted['session_id']
        assert entered.wait(30)
        assert Path(accepted['output_path']).exists()
        value = client.status(sid)
        assert not value['output_completed'] and value['final_output_path'] is None
        assert client.stop(sid)['stop_result'] == 'capture_already_closed'
        release.set()
        wait_for(lambda: runtime.paused == 'finalizer_needs_attention')
        value = client.status(sid)
        assert value['output_completed'] and value['final_output_path'] == accepted['output_path']
        assert 'secret' not in str(client.health())
        assert runtime.journal._read(lambda db: db.execute('SELECT count(*) FROM release_results').fetchone()[0]) == 1
    finally:
        release.set()
        server.server_close()
