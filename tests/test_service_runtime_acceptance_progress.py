"""Independent connected writer-progress, eight-unit and FIFO acceptance review."""

import os
from pathlib import Path
from threading import Event

import pytest

pytestmark = pytest.mark.skipif(os.name != 'nt', reason='native Windows runtime')

from tests.service_runtime_helpers import runtime_case, managed_process, start, wait_for, hashes, preserved
from tests.runtime_acceptance_helpers import progressing_sources, immutable_session, file_hashes
from tikrec.recording import RecordingBusy


@pytest.mark.parametrize('different', [False, True])
def test_two_writers_progress_beside_fifo_at_eight_units(runtime_case, different):
    case = runtime_case
    if different:
        case.different.add('old')
    entered, release = Event(), Event()
    case.releases.append(release)
    claimed, plans, originals = [], [], {}
    runtime = case.build().start_runtime()
    barriers, data = progressing_sources(case, runtime, ('writer-a', 'writer-b'))
    source_paths = list(runtime.root.parent.glob('source-*.flv'))
    source_before = file_hashes(source_paths)

    def fault(point):
        adapter = runtime.current
        if point == 'after_claim':
            claimed.append(adapter.coordinator.claimed['session_id'])
        if point == 'after_media_plan':
            sid = adapter.coordinator.claimed['session_id']
            plans.append(adapter.manifest.publication.validation.assembly.plan.stream_copy)
            originals[sid] = (adapter.coordinator.token,
                hashes(Path(runtime.session_status(sid)['parts_directory']), adapter))
            if len(plans) == 1:
                entered.set()
                assert release.wait(90)

    case.fault = fault
    accepted = [start(runtime, 'old', room='100', raw=True)]
    assert entered.wait(30)
    for index in range(1, 6):
        item = start(runtime, 'queued-' + str(index), room=str(100 + index), raw=False)
        accepted.append(item)
        wait_for(lambda: runtime.journal.session(item['session_id'])['phase'] == 'queued')
    old_identity, handoffs = immutable_session(runtime.journal, accepted[0]['session_id'])
    writers = [start(runtime, name, room=str(200 + index), raw=not index,
                     creator='example.creator' if index == 0 else 'example.other')
               for index, name in enumerate(barriers)]
    entries = [runtime.captures[item['session_id']] for item in writers]
    for name in barriers:
        assert barriers[name][0][0].wait(10)
    first_counts = [runtime.session_status(item['session_id'])['bytes_written'] for item in writers]
    assert all(count > 0 for count in first_counts)
    assert len(runtime.journal.status()['units']) == 8
    with pytest.raises(RecordingBusy, match='finalization_backlog_full'):
        start(runtime, 'overflow', room='300', creator='example.overflow', raw=False)
    assert not (runtime.root / 'overflow.parts').exists()
    for _, advance in barriers.values():
        advance[0].set()
    for ready, _ in barriers.values():
        assert ready[1].wait(10)
    assert all(runtime.session_status(item['session_id'])['bytes_written'] > count
               for item, count in zip(writers, first_counts))
    assert all(entry['thread'].is_alive() and not entry['done'] for entry in entries)
    assert runtime.health()['active_count'] == 2
    assert claimed == [accepted[0]['session_id']]
    assert sum(task['state'] == 'running' for task in runtime.journal.status()['tasks']) == 1
    assert runtime.stop(accepted[0]['session_id'])['stop_result'] == 'capture_already_closed'
    for item in writers:
        assert not runtime.capture_callback(accepted[0]['session_id'], item['generation'], 'heartbeat', 'stale', 999999)
    release.set()
    wait_for(lambda: all(runtime.session_status(item['session_id'])['output_completed'] for item in accepted), 150)
    assert claimed == [item['session_id'] for item in accepted]
    assert plans == [not different, True, True, True, True, True]
    assert len(runtime.journal.status()['units']) == 2
    assert all(runtime.session_status(item['session_id'])['active'] for item in writers)
    assert immutable_session(runtime.journal, accepted[0]['session_id']) == (old_identity, handoffs)
    for item, (_, advance) in zip(writers, barriers.values()):
        advance[1].set()
        wait_for(lambda: runtime.session_status(item['session_id'])['output_completed'])
    wait_for(lambda: not runtime.journal.status()['units'], 90)
    assert claimed == [item['session_id'] for item in (*accepted, *writers)]
    for item in (*accepted, *writers):
        sid = item['session_id']
        assert runtime.session_status(sid)['output_completed']
        token, before = originals[sid]
        preserved(before, token)
    raw_root = runtime.root / 'writer-a.parts'
    assert (raw_root / 'connection-0001.raw').read_bytes() == data
    assert list(raw_root.glob('*.arrival*'))
    assert not list((runtime.root / 'writer-b.parts').glob('*.raw'))
    assert file_hashes(source_paths) == source_before
    assert runtime.journal._read(lambda db: db.execute('SELECT count(*) FROM release_results').fetchone()[0]) == 8
    assert runtime.shutdown()['complete']
    assert all(not entry['thread'].is_alive() for entry in entries)
    assert not runtime.connections.has_ownership() and not runtime.authority._attempts
