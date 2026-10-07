"""Reserved H units, backlog and storage barriers with actual capture work."""

import os
from threading import Event

import pytest

pytestmark = pytest.mark.skipif(os.name != 'nt', reason='native Windows runtime')

from tests.service_runtime_helpers import runtime_case, managed_process, start, wait_for
from tikrec.recording import RecordingBusy
from tikrec.recording_manager import RecordingNotFound


def test_six_tasks_two_captures_eight_units_then_fifo_returns_capacity(runtime_case):
    case = runtime_case
    entered, release = Event(), Event()
    case.releases.append(release)
    once = []
    def fault(point):
        if point == 'after_media_plan' and not once:
            once.append(True)
            entered.set()
            assert release.wait(45)
    case.fault = fault
    runtime = case.build().start_runtime()
    successes = [start(runtime, 'task0', room='100', raw=False)]
    assert entered.wait(30)
    for index in range(1, 6):
        accepted = start(runtime, 'task' + str(index), room=str(100 + index), raw=False)
        successes.append(accepted)
        wait_for(lambda: runtime.journal.session(accepted['session_id'])['phase'] == 'queued')
    a_entered, a_release = case.hold('a')
    b_entered, b_release = case.hold('b')
    a = start(runtime, 'a', room='200', raw=False)
    b = start(runtime, 'b', room='201', creator='example.second', raw=False)
    assert a_entered.wait(10) and b_entered.wait(10)
    assert len(runtime.journal.status()['units']) == 8
    with pytest.raises(RecordingBusy, match='finalization_backlog_full'):
        start(runtime, 'overflow', room='300', creator='example.third')
    assert not (runtime.root / 'overflow.parts').exists()
    a_release.set()
    b_release.set()
    wait_for(lambda: len(runtime.journal.status()['tasks']) == 8)
    assert len(runtime.journal.status()['units']) == 8
    assert runtime.health()['active_count'] == 0
    release.set()
    wait_for(lambda: not runtime.journal.status()['units'], timeout=150)
    for accepted in (*successes, a, b):
        assert runtime.session_status(accepted['session_id'])['output_completed']
    terminal = runtime.journal.history()
    assert len(terminal) == 8


def test_storage_refuses_admission_and_defers_finalizer_without_refund(runtime_case):
    case = runtime_case
    entered, release = case.hold('one')
    runtime = case.build().start_runtime()
    accepted = start(runtime, 'one')
    assert entered.wait(10)
    case.free = 0
    with pytest.raises(RecordingBusy, match='low_free_space'):
        start(runtime, 'low', room='456', creator='example.second')
    release.set()
    wait_for(lambda: runtime.paused == 'low_free_space')
    assert runtime.journal.session(accepted['session_id'])['phase'] == 'queued'
    assert len(runtime.journal.status()['units']) == 1
    assert not (runtime.root / 'one.mp4').exists()
    case.free = 100 * 1024**3
    wait_for(lambda: runtime.session_status(accepted['session_id'])['output_completed'])


def test_targeted_stop_active_capture_and_terminal_not_found(runtime_case):
    case = runtime_case
    entered, release = case.hold('one')
    case.cooperative.add('one')
    runtime = case.build().start_runtime()
    accepted = start(runtime, 'one')
    assert entered.wait(10)
    runtime.stop(accepted['session_id'])
    assert runtime.captures[accepted['session_id']]['bridge'].stop_event.is_set()
    release.set()
    wait_for(lambda: runtime.journal.session(accepted['session_id'])['phase'] in {'completed', 'no_assembly'})
    with pytest.raises(RecordingNotFound):
        runtime.stop(accepted['session_id'])


def test_unavailable_catalog_storage_blocks_manual_and_finalizer_launch(runtime_case):
    from tikrec.storage_status import StorageStatus
    case = runtime_case
    available = [False]
    def usage(path):
        if not available[0]:
            raise OSError('catalog volume unavailable')
        from types import SimpleNamespace
        return SimpleNamespace(free=100 * 1024**3)
    # The case builder's catalog and root share this exact disposable parent layout.
    probe = case.build()
    catalog = StorageStatus(probe.journal.path.parent, disk_usage=usage)
    assert probe.shutdown()['complete']
    runtime = case.build(catalog_storage=catalog).start_runtime()
    with pytest.raises(RecordingBusy, match='storage_unavailable'):
        start(runtime, 'unavailable')
    assert not runtime.journal.history()
    available[0] = True
    ready, release = case.hold('one')
    accepted = start(runtime, 'one')
    assert ready.wait(10)
    available[0] = False
    release.set()
    wait_for(lambda: runtime.paused == 'storage_unavailable')
    assert runtime.journal.session(accepted['session_id'])['phase'] == 'queued'
    assert len(runtime.journal.status()['units']) == 1
    available[0] = True
    wait_for(lambda: runtime.session_status(accepted['session_id'])['output_completed'])
