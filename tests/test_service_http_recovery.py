"""Stable transport truth across accepted prepared-success restart recovery only."""

import os
from threading import Event

import pytest

pytestmark = pytest.mark.skipif(os.name != 'nt', reason='native Windows runtime')

from tests.service_runtime_helpers import runtime_case, managed_process, wait_for, hashes
from tests.service_http_helpers import compose, start_http


def test_http_uuid_lookup_before_after_prepared_restart_and_terminal_ack_loss(runtime_case, tmp_path):
    case = runtime_case
    def fault(point):
        if point == 'before_terminal_release':
            raise OSError('prepared bookkeeping interrupted')
    case.fault = fault
    server, client = compose(case, tmp_path)
    try:
        accepted = start_http(client, server.runtime, 'prepared', raw=True)
        sid = accepted['session_id']
        wait_for(lambda: server.runtime.paused == 'finalizer_needs_attention')
        value = client.status(sid)
        assert not value['output_completed'] and value['final_output_path'] is None
        row = server.runtime.journal.session(sid)
        token = row['task']['token']
        record = server.runtime.journal.settlement(token)
        handoff = server.runtime.journal.operation(record['preparation']['binding']['h_operation'])
        before = hashes(server.runtime.root / 'prepared.parts')
        assert server.shutdown_components()['complete']
    finally:
        server.server_close()
    case.fault = lambda _: None
    entered, release = Event(), Event()
    case.releases.append(release)
    def recovery_fault(point):
        if point == 'after_recovery_authority':
            entered.set()
            assert release.wait(45)
        if point == 'after_recovery_terminal':
            raise OSError('recovered terminal reporting acknowledgement lost')
    fresh = case.build(recovery_fault=recovery_fault)
    restarted, current = compose(case, tmp_path, runtime=fresh)
    try:
        assert entered.wait(30)
        assert not current.status(sid)['output_completed']
        assert current.stop(sid)['stop_result'] == 'capture_already_closed'
        assert current.recordings()['outstanding_sessions'][0]['session_id'] == sid
        release.set()
        wait_for(lambda: fresh.paused == 'finalizer_needs_attention')
        value = current.status(sid)
        assert value['output_completed'] and value['final_output_path'] == accepted['output_path']
        assert value['origin_slot_id'] == accepted['origin_slot_id'] and value['raw_copy_enabled']
        assert hashes(fresh.root / 'prepared.parts') == before
        assert fresh.journal.operation(record['preparation']['binding']['h_operation']) == handoff
        assert all(fresh.journal.session(sid)[key] == row[key] for key in
                   ('intent', 'seal', 'seal_hash', 'generation', 'origin_slot'))
        assert fresh.journal._read(lambda db: db.execute('SELECT count(*) FROM release_results').fetchone()[0]) == 0
        assert fresh.journal._read(lambda db: db.execute('SELECT count(*) FROM release_recovery_results').fetchone()[0]) == 1
        assert not fresh.journal.status()['units']
        assert restarted.shutdown_components()['complete']
    finally:
        release.set()
        restarted.server_close()
