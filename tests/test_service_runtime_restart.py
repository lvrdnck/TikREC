"""Connected restart uses only queued work and accepted prepared-success recovery."""

import json
import os
import shutil
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(os.name != 'nt', reason='native Windows runtime death')

from tests.service_runtime_helpers import managed_process, runtime_case, start, wait_for, hashes
from tests.capture_handoff_helpers import observations
from tests.owned_process_helpers import Events
from tests.test_journal_settlement_recovery_death import _kill, _wait_for_barrier, _child_import_path
from tikrec.owned_process_api import kernel
from tikrec.service_runtime import IsolatedServiceRuntime
from tikrec.session_journal import SessionJournal


@pytest.mark.parametrize('mode', ['before_terminal_release', 'after_terminal_release', 'after_claim'])
def test_actual_runtime_supervisor_death_and_bounded_restart(tmp_path, managed_process, monkeypatch, mode):
    _child_import_path(monkeypatch)
    api = kernel()
    with Events() as barrier:
        supervisor = managed_process()
        supervisor.start(Path(sys._base_executable), ['-m', 'tests.service_runtime_death_probe',
            mode, str(tmp_path), *barrier.names], cwd=tmp_path, before_resume=lambda value: value)
        _wait_for_barrier(barrier, supervisor)
        context = json.loads((tmp_path / 'runtime-context.json').read_text())
        _kill(api, supervisor)
    journal, root = SessionJournal(Path(context['path']), context['catalog']), Path(context['root'])
    old = journal.session(context['session'])
    before = hashes(root / 'old.parts')
    if mode == 'before_terminal_release':
        with Events() as barrier:
            recovery_supervisor = managed_process()
            recovery_supervisor.start(Path(sys._base_executable), ['-m', 'tests.service_runtime_death_probe',
                'recovery:after_recovery_authority', str(tmp_path), *barrier.names],
                cwd=tmp_path, before_resume=lambda value: value)
            _wait_for_barrier(barrier, recovery_supervisor)
            _kill(api, recovery_supervisor)
        assert journal.release_recovery(context['token'])['head']['generation'] == 1
    runtime = IsolatedServiceRuntime(journal, root,
        ffmpeg=Path(shutil.which('ffmpeg')).resolve(), ffprobe=Path(shutil.which('ffprobe')).resolve(),
        observations=lambda bridge: observations((tmp_path / 'fixture.flv').read_bytes(),
                                                  room=bridge.intent.expected_room))
    # Plain construction leaves durable phases unchanged.
    assert journal.session(context['session']) == old
    try:
        runtime.start_runtime()
        if mode == 'after_claim':
            wait_for(lambda: runtime.paused == 'unsupported_unfinished_phase')
            assert len(journal.status()['units']) == 2
            assert journal.session(context['session'])['task']['state'] == 'running'
            assert not (root / 'old.mp4').exists()
            disjoint = start(runtime, 'disjoint', room='789', creator='example.second', raw=False)
            wait_for(lambda: journal.session(disjoint['session_id'])['phase'] == 'queued')
            assert len(journal.status()['units']) == 3
            assert runtime.session_status(context['session'])['needs_attention']
        else:
            wait_for(lambda: not journal.status()['units'])
            assert hashes(root / 'old.parts') == before
            assert all(row['phase'] == 'completed' for row in journal.history())
            if mode == 'before_terminal_release':
                assert journal.release_recovery(context['token'])['head']['generation'] == 2
            else:
                assert journal.release_recovery(context['token']) is None
            assert runtime.session_status(context['session'])['output_completed']
        assert runtime.health()['available_slots'] == 2
    finally:
        assert runtime.shutdown()['complete']


def test_unsupported_reserved_start_stays_pinned_without_source_reopen(runtime_case):
    case = runtime_case
    from threading import Thread
    def factory(**options):
        if options['name'].startswith('tikrec-isolated-capture'):
            raise OSError('capture launch failed')
        return Thread(**options)
    first = case.build(thread_factory=factory).start_runtime()
    with pytest.raises(OSError, match='capture launch failed'):
        start(first, 'unsupported')
    sid = first.latest[1]
    assert len(first.journal.status()['units']) == 1
    # Explicitly retire a never-launched lease; accepted intent remains durable.
    first.captures[sid]['bridge'].lease.close()
    first.captures[sid]['bridge'].fence.close()
    assert first.shutdown()['complete']
    second = case.build().start_runtime()
    assert second.session_status(sid)['needs_attention']
    assert second.health()['available_slots'] == 1
    assert len(second.journal.status()['units']) == 1
    assert second.stop(sid)['stop_result'] == 'capture_needs_attention'


def test_supervisor_setup_wait_remains_bounded_and_requires_exact_native_event():
    """Extra setup time cannot substitute for an actual owned supervisor barrier."""
    with Events() as barrier:
        with pytest.raises(AssertionError, match='child barrier not reached'):
            barrier.wait(timeout_ms=10)
        with pytest.raises(AssertionError, match='invalid fixture wait bound'):
            barrier.wait(timeout_ms=30001)
        barrier.release(0)
        barrier.wait(timeout_ms=30000)
