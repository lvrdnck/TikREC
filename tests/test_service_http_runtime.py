"""Connected transport semantics across actual capture, FIFO, terminal history and restart."""

import os
from pathlib import Path
from threading import Event

import pytest

pytestmark = pytest.mark.skipif(os.name != 'nt', reason='native Windows runtime')

from tests.service_runtime_helpers import runtime_case, managed_process, wait_for, hashes, preserved
from tests.runtime_acceptance_helpers import progressing_sources, immutable_session, file_hashes
from tests.service_http_helpers import compose, start_http, dispatch, response
from tikrec.remote import RemoteError


@pytest.mark.parametrize('different', [False, True])
def test_http_client_old_uuid_two_progressing_captures_backlog_and_restart(runtime_case, tmp_path, different):
    case = runtime_case
    if different:
        case.different.add('old')
    entered, release = Event(), Event()
    case.releases.append(release)
    originals, plans = {}, []
    server, client = compose(case, tmp_path)
    runtime = server.runtime
    # Install the original whole-tag barriers after resolver composition.
    barriers, data = progressing_sources(case, runtime, ('writer-a', 'writer-b'))
    # Progress helper's fixture expected room must be proved by its HTTP resolver.
    supplied = runtime.observations
    from tests.capture_handoff_helpers import observations
    from tikrec.tiktok import _ResolvedLiveUrl, TikTokOfflineError
    def observed(bridge):
        result = supplied(bridge)
        if Path(bridge.intent.output_path).stem in barriers:
            room = '2001' if bridge.intent.creator == 'example.creator' else '2002'
            actions = iter([_ResolvedLiveUrl('https://fixture.invalid/source.flv', 2, room_id=room),
                            TikTokOfflineError('fixture ended', room_id=room)])
            def resolve(_):
                item = next(actions)
                if isinstance(item, Exception):
                    raise item
                return item
            result['resolver'] = resolve
        return result
    runtime.observations = observed
    sources = list(runtime.root.parent.glob('source-*.flv'))
    source_before = file_hashes(sources)
    def fault(point):
        adapter = runtime.current
        if point == 'after_media_plan':
            sid = adapter.coordinator.claimed['session_id']
            plans.append(adapter.manifest.publication.validation.assembly.plan.stream_copy)
            originals[sid] = (adapter.coordinator.token,
                hashes(Path(runtime.session_status(sid)['parts_directory']), adapter))
            if len(plans) == 1:
                entered.set()
                assert release.wait(150)
    case.fault = fault
    try:
        old = start_http(client, runtime, 'old', raw=True, creator='example.old')
        assert entered.wait(30)
        identity = immutable_session(runtime.journal, old['session_id'])
        old_status = client.status(old['session_id'])
        assert not old_status['active'] and not old_status['output_completed']
        assert old_status['final_output_path'] is None
        accepted = [old]
        for index in range(5):
            item = start_http(client, runtime, 'queued-' + str(index), creator='example.queue' + str(index))
            accepted.append(item)
            wait_for(lambda: runtime.journal.session(item['session_id'])['phase'] == 'queued')
        writers = [start_http(client, runtime, name, raw=not index,
            creator='example.creator' if index == 0 else 'example.other')
            for index, name in enumerate(barriers)]
        for ready, _ in barriers.values():
            assert ready[0].wait(15)
        counts = [client.status(item['session_id'])['bytes_written'] for item in writers]
        assert all(count > 0 for count in counts)
        aggregate = client.recordings()
        assert aggregate['capacity'] == 2 and len(aggregate['slots']) == 2
        assert aggregate['active_count'] == 2 and aggregate['finalization']['outstanding_units'] == 8
        assert aggregate['admission_reason'] == 'finalization_backlog_full'
        assert len(aggregate['finalization_sessions']) == 6
        with pytest.raises(RemoteError, match='HTTP 409'):
            start_http(client, runtime, 'overflow', creator='example.overflow')
        for operation in (client.status, client.stop):
            with pytest.raises(RemoteError, match='HTTP 409'):
                operation()
        assert client.stop(old['session_id'])['stop_result'] == 'capture_already_closed'
        assert all(not runtime.captures[item['session_id']]['bridge'].stop_event.is_set() for item in writers)
        for ready, advance in barriers.values():
            advance[0].set()
            assert ready[1].wait(15)
        assert all(client.status(item['session_id'])['bytes_written'] > count
                   for item, count in zip(writers, counts))
        assert client.status(old['session_id'])['origin_slot_id'] == old['origin_slot_id']
        assert client.status(old['session_id'])['raw_copy_enabled']
        release.set()
        # Keep both writers progressing through this old task, without holding them
        # past their source deadline while five unrelated queued tasks finish.
        wait_for(lambda: runtime.session_status(old['session_id'])['output_completed'], 60)
        for item in writers:
            assert client.status(item['session_id'])['active']
        # Capture capacity can be physically free while eight older artifact units refuse admission.
        assert client.stop(writers[0]['session_id'])['stop_requested']
        assert not runtime.captures[writers[1]['session_id']]['bridge'].stop_event.is_set()
        for _, advance in barriers.values():
            advance[1].set()
        wait_for(lambda: not runtime.journal.status()['units'], 180)
        assert plans == [not different, True, True, True, True, True, True, True]
        for item in (*accepted, *writers):
            status = client.status(item['session_id'])
            assert status['output_completed'] and status['final_output_path'] == item['output_path']
            token, before = originals[item['session_id']]
            preserved(before, token)
        after_identity, after_h = immutable_session(runtime.journal, old['session_id'])
        assert after_identity == identity[0]
        assert all(receipt in after_h for receipt in identity[1]) and len(after_h) == 8
        assert file_hashes(sources) == source_before
        assert (runtime.root / 'writer-a.parts' / 'connection-0001.raw').read_bytes() == data
        assert not list((runtime.root / 'writer-b.parts').glob('*.raw'))
        assert runtime.journal._read(lambda db: db.execute('SELECT count(*) FROM release_results').fetchone()[0]) == 8
        assert server.shutdown_components()['complete']
        assert not server.requests.owners and not runtime.connections.has_ownership()
    finally:
        release.set()
        for _, advance in barriers.values():
            for event in advance:
                event.set()
        server.server_close()
    restarted, current = compose(case, tmp_path, runtime=case.build())
    try:
        status = current.status(old['session_id'])
        assert status['output_completed'] and status['origin_slot_id'] == old['origin_slot_id']
        assert status['bytes_written'] is None
        with pytest.raises(RemoteError, match='HTTP 404'):
            current.stop(old['session_id'])
        assert len(restarted.runtime.journal.history()) == 8
    finally:
        restarted.server_close()


def test_free_physical_slots_are_distinct_from_eight_unit_admission(runtime_case, tmp_path):
    case = runtime_case
    entered, release = Event(), Event()
    case.releases.append(release)
    def fault(point):
        if point == 'after_media_plan':
            entered.set()
            assert release.wait(150)
    case.fault = fault
    server, client = compose(case, tmp_path)
    try:
        for index in range(8):
            item = start_http(client, server.runtime, 'task-' + str(index), creator='example.task' + str(index))
            wait_for(lambda: not server.runtime.session_status(item['session_id'])['active'])
            if index == 0:
                assert entered.wait(30)
        health = client.health()
        assert health['available_slots'] == 2 and health['available']
        assert not health['admission_available'] and health['admission_reason'] == 'finalization_backlog_full'
        assert len(client.recordings()['finalization_sessions']) == 8
        with pytest.raises(RemoteError, match='HTTP 409'):
            start_http(client, server.runtime, 'refused')
        assert not (server.runtime.root / 'refused.parts').exists()
    finally:
        release.set()
        server.server_close()
