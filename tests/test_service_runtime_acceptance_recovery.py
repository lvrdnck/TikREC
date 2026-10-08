"""Connected startup recovery while writers progress; terminal reporting is local."""

import os
from threading import Event
from types import SimpleNamespace

import pytest

pytestmark = pytest.mark.skipif(os.name != 'nt', reason='native Windows runtime')

from tests.service_runtime_helpers import runtime_case, managed_process, start, wait_for, hashes
from tests.runtime_acceptance_helpers import progressing_sources
from tests.test_service_runtime_recovery import prepared_runtime
from tikrec.storage_status import StorageStatus, GIB


def test_catalog_deferred_recovery_with_two_progressing_captures_and_terminal_report_loss(runtime_case):
    case = runtime_case
    original, prepared, queued, token, before = prepared_runtime(case)
    prepared_sid = prepared['session_id']
    old = original.journal.session(prepared_sid)
    record = original.journal.settlement(token)
    handoff_id = record['preparation']['binding']['h_operation']
    handoff = original.journal.operation(handoff_id)
    entered, release = Event(), Event()
    case.releases.append(release)
    first = OSError('independent recovered terminal reporting loss')
    catalog_free = [0]
    catalog = StorageStatus(original.journal.path.parent,
        disk_usage=lambda _: SimpleNamespace(free=catalog_free[0]))

    def recovery_fault(point):
        if point == 'after_recovery_authority':
            entered.set()
            assert release.wait(90)
        if point == 'after_recovery_terminal':
            raise first

    runtime = case.build(catalog_storage=catalog, recovery_fault=recovery_fault)
    barriers, data = progressing_sources(case, runtime, ('writer-a', 'writer-b'))
    assert runtime.journal.session(prepared_sid) == old
    runtime.start_runtime()
    wait_for(lambda: runtime.paused == 'low_free_space')
    assert runtime.storage.snapshot()['state'] == 'ok'
    assert runtime.journal.release_recovery(token) is None
    assert len(runtime.journal.status()['units']) == 2
    assert hashes(runtime.root / 'prepared.parts') == before
    catalog_free[0] = 100 * GIB
    assert entered.wait(30)
    writers = []
    for index, name in enumerate(barriers):
        writers.append(start(runtime, name, room=str(800 + index), raw=not index,
            creator='example.creator' if index == 0 else 'example.other'))
    for ready, _ in barriers.values():
        assert ready[0].wait(10)
    counts = [runtime.session_status(item['session_id'])['bytes_written'] for item in writers]
    assert all(count > 0 for count in counts)
    for _, advance in barriers.values():
        advance[0].set()
    for ready, _ in barriers.values():
        assert ready[1].wait(10)
    assert all(runtime.session_status(item['session_id'])['bytes_written'] > count
               for item, count in zip(writers, counts))
    assert runtime.health()['active_count'] == 2
    assert len(runtime.journal.status()['units']) == 4
    assert runtime.journal.release_recovery(token)['head']['generation'] == 1
    release.set()
    wait_for(lambda: runtime.paused == 'finalizer_needs_attention')
    assert runtime.errors[0] is first
    assert runtime.session_status(prepared_sid)['output_completed']
    assert len(runtime.journal.status()['units']) == 3
    assert hashes(runtime.root / 'prepared.parts') == before
    assert runtime.journal.operation(handoff_id) == handoff
    assert runtime.journal.settlement(token)['cleanup'] == record['cleanup']
    for item, (_, advance) in zip(writers, barriers.values()):
        advance[1].set()
        wait_for(lambda: runtime.journal.session(item['session_id'])['phase'] == 'queued')
    assert runtime.shutdown()['complete']
    assert not runtime.connections.has_ownership()
    assert all(not owner.has_retained_ownership() for owner in runtime.authority._recovery_owners.values())
    assert len(runtime.journal.status()['units']) == 3
    resumed = case.build()
    assert resumed.journal.release_recovery(token)['head']['generation'] == 1
    resumed.start_runtime()
    wait_for(lambda: not resumed.journal.status()['units'])
    assert all(resumed.session_status(item['session_id'])['output_completed'] for item in (prepared, queued, *writers))
    assert resumed.journal.release_recovery(token)['head']['generation'] == 1
    assert resumed.journal._read(lambda db: db.execute('SELECT count(*) FROM release_results').fetchone()[0]) == 3
    assert resumed.journal._read(lambda db: db.execute('SELECT count(*) FROM release_recovery_results').fetchone()[0]) == 1
    assert hashes(resumed.root / 'prepared.parts') == before
    assert (resumed.root / 'writer-a.parts' / 'connection-0001.raw').read_bytes() == data
    assert not list((resumed.root / 'writer-b.parts').glob('*.raw'))
    assert resumed.shutdown()['complete']
