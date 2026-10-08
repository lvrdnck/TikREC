"""Connected projection truth and fixed redaction under failed/empty/output states."""

import os
from pathlib import Path
from threading import Event

import pytest

pytestmark = pytest.mark.skipif(os.name != 'nt', reason='native Windows runtime')

from tests.service_runtime_helpers import runtime_case, managed_process, wait_for
from tests.service_http_helpers import compose, start_http, dispatch, response
from tikrec.remote import RemoteError
from tikrec.tiktok import TikTokOfflineError


def test_admitted_empty_evidence_stays_visible_after_slot_reuse(runtime_case, tmp_path):
    from tests.capture_handoff_helpers import observations
    server, client = compose(runtime_case, tmp_path)
    runtime = server.runtime
    original = runtime.observations
    def supplied(bridge):
        if Path(bridge.intent.output_path).stem == 'empty-evidence':
            value = observations(b'', room='123')
            value['tag_source'] = lambda _: iter(())
            return value
        return original(bridge)
    runtime.observations = supplied
    try:
        old = start_http(client, runtime, 'empty-evidence')
        sid = old['session_id']
        wait_for(lambda: runtime.journal.session(sid)['phase'] == 'no_assembly')
        assert runtime.journal.status()['units'][0]['kind'] == 'evidence'
        ready, release = runtime_case.hold('replacement')
        new = start_http(client, runtime, 'replacement', creator='example.replacement')
        assert ready.wait(10) and new['slot_id'] == old['slot_id']
        value = client.recordings()
        assert not value['finalization_sessions']
        assert {item['session_id'] for item in value['outstanding_sessions']} == {sid, new['session_id']}
        assert not client.status(sid)['output_completed']
        assert client.status(sid)['finalization_state'] == 'no_assembly'
        release.set()
    finally:
        for _, release in runtime_case.holds.values():
            release.set()
        server.server_close()


def test_empty_capture_is_terminal_without_invented_mp4(runtime_case, tmp_path):
    server, client = compose(runtime_case, tmp_path)
    runtime = server.runtime
    original = runtime.observations
    def supplied(bridge):
        value = original(bridge)
        value['resolver'] = lambda _: (_ for _ in ()).throw(TikTokOfflineError('fixture offline'))
        return value
    runtime.observations = supplied
    try:
        accepted = start_http(client, runtime, 'empty')
        sid = accepted['session_id']
        wait_for(lambda: runtime.journal.session(sid)['phase'] == 'no_assembly')
        value = client.status(sid)
        assert not value['active'] and not value['output_completed']
        assert value['final_output_path'] is None and value['finalization_state'] == 'no_assembly'
        assert not Path(accepted['output_path']).exists()
        with pytest.raises(RemoteError, match='HTTP 404'):
            client.stop(sid)
    finally:
        server.server_close()


def test_output_collision_stays_outstanding_and_cannot_claim_completion(runtime_case, tmp_path):
    case = runtime_case
    collided = []
    def fault(point):
        if point == 'after_media_plan' and not collided:
            output = server.runtime.root / 'collision.mp4'
            output.write_bytes(b'external collision')
            collided.append(output)
    case.fault = fault
    server, client = compose(case, tmp_path)
    try:
        accepted = start_http(client, server.runtime, 'collision')
        wait_for(lambda: server.runtime.paused == 'finalizer_needs_attention')
        assert collided and collided[0].read_bytes() == b'external collision'
        value = client.status(accepted['session_id'])
        assert not value['output_completed'] and value['final_output_path'] is None
        assert value['needs_attention'] and not value['active']
        assert client.health()['finalization']['outstanding_units'] == 1
        assert client.stop(accepted['session_id'])['stop_result'] == 'capture_already_closed'
    finally:
        server.server_close()


def test_catalog_query_error_and_forged_completion_never_export_output(runtime_case, tmp_path, monkeypatch):
    server, client = compose(runtime_case, tmp_path)
    runtime = server.runtime
    original = runtime.connections.original
    def unavailable():
        import threading
        if threading.current_thread().name == 'tikrec-isolated-http':
            raise OSError('private SQLite signed://secret')
        return original()
    try:
        monkeypatch.setattr(runtime.connections, 'original', unavailable)
        health = client.health()
        assert health['active_count'] is None and health['available_slots'] is None
        assert health['finalization']['outstanding_units'] is None
        assert 'secret' not in str(health)
        code, value = response(dispatch(server, 'GET', '/recordings'))
        assert code == 500 and value == {'error': 'service status unavailable'}
        monkeypatch.setattr(runtime.connections, 'original', original)
        # Even a damaged in-memory projection cannot substitute for owned terminal proof.
        ready, done = runtime_case.hold('capturing')
        accepted = start_http(client, runtime, 'capturing')
        assert ready.wait(10)
        status = runtime.session_status
        monkeypatch.setattr(runtime, 'session_status', lambda sid: {**status(sid), 'output_completed': True})
        code, value = response(dispatch(server, 'GET', '/sessions/' + accepted['session_id']))
        assert code == 500 and value == {'error': 'service status unavailable'}
        monkeypatch.setattr(runtime, 'session_status', status)
        done.set()
    finally:
        for _, done in runtime_case.holds.values():
            done.set()
        server.server_close()


def test_allowlisted_projection_drops_arbitrary_nested_state_and_bounds_responses(runtime_case, tmp_path, monkeypatch):
    case = runtime_case
    ready, done = case.hold('poison')
    server, client = compose(case, tmp_path)
    runtime = server.runtime
    try:
        accepted = start_http(client, runtime, 'poison')
        assert ready.wait(10)
        original = runtime.session_status
        monkeypatch.setattr(runtime, 'session_status', lambda sid: {**original(sid),
            'source_url': 'https://signed.invalid/secret', 'error': 'secret exception',
            'sqlite': {'capability': 'secret'}, 'stderr': 'secret'})
        value = client.status(accepted['session_id'])
        assert 'secret' not in str(value) and value['source_url'].endswith('/@example.creator/live')
        assert value['error'] == 'transport_needs_attention'
        monkeypatch.setattr(server.controller, 'status', lambda: {'blob': 'secret' * 12000})
        code, value = response(dispatch(server, 'GET', '/recording'))
        assert code == 500 and value == {'error': 'service response exceeds transport bound'}
        monkeypatch.setattr(server.monitor, 'snapshot', lambda: {'creators': [{}] * 101})
        code, value = response(dispatch(server, 'GET', '/monitoring'))
        assert code == 500 and value == {'error': 'service status unavailable'}
    finally:
        done.set()
        server.server_close()
