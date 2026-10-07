"""Real capture/H -> managed FIFO -> publication/manifest/settlement integration."""

import os
from threading import Event

import pytest

pytestmark = pytest.mark.skipif(os.name != 'nt', reason='native Windows runtime')

from tests.service_runtime_helpers import runtime_case, managed_process, start, wait_for, hashes, preserved
from tikrec.recording import RecordingBusy
from tikrec.recording_manager import RecordingAmbiguous, RecordingDuplicate


@pytest.mark.parametrize('different', [False, True])
def test_connected_automatic_finalization_and_preserved_truth(runtime_case, different):
    case = runtime_case
    if different:
        case.different.add('one')
    entered, release = Event(), Event()
    case.releases.append(release)
    def fault(point):
        if point == 'after_media_plan':
            entered.set()
            assert release.wait(45)
    case.fault = fault
    runtime = case.build().start_runtime()
    accepted = start(runtime, 'one')
    sid = accepted['session_id']
    assert entered.wait(30)
    original = runtime.journal.session(sid)
    h = runtime.journal._read(lambda db: [tuple(row) for row in db.execute(
        "SELECT * FROM operations WHERE kind='handoff'")])
    before = hashes(runtime.root / 'one.parts', runtime.current)
    assert runtime.health()['available_slots'] == 2
    assert runtime.session_status(sid)['state'] == 'finalizing'
    assert runtime.session_status(sid)['final_output_path'] is None
    token = runtime.current.coordinator.token
    assert runtime.current.manifest.publication.validation.assembly.plan.stream_copy is not different
    release.set()
    wait_for(lambda: runtime.session_status(sid)['output_completed'])
    wait_for(lambda: runtime.current is None)
    preserved(before, token)
    current = runtime.journal.session(sid)
    assert all(current[k] == original[k] for k in ('intent', 'seal', 'seal_hash', 'generation', 'origin_slot'))
    assert runtime.journal._read(lambda db: [tuple(row) for row in db.execute(
        "SELECT * FROM operations WHERE kind='handoff'")]) == h
    assert runtime.health()['finalization']['outstanding_units'] == 0
    assert runtime.authority._attempts == {}


def test_same_creator_new_room_two_queued_plus_two_captures(runtime_case):
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
    old = start(runtime, 'old', room='123')
    assert entered.wait(30)
    queued = start(runtime, 'queued', room='456', raw=False)
    wait_for(lambda: runtime.journal.session(queued['session_id'])['phase'] == 'queued')
    a_entered, a_release = case.hold('a')
    b_entered, b_release = case.hold('b')
    a = start(runtime, 'a', room='789', raw=True)
    b = start(runtime, 'b', room='987', creator='example.second', raw=False)
    assert a_entered.wait(10) and b_entered.wait(10)
    assert runtime.health()['active_count'] == 2
    assert len(runtime.journal.status()['tasks']) == 2
    assert sum(t['state'] == 'running' for t in runtime.journal.status()['tasks']) == 1
    assert runtime.worker.daemon is False
    assert runtime.stop(old['session_id'])['stop_result'] == 'capture_already_closed'
    assert not runtime.captures[a['session_id']]['bridge'].stop_event.is_set()
    assert not runtime.capture_callback(old['session_id'], old['generation'], 'state', 'failed')
    with pytest.raises(RecordingAmbiguous):
        runtime.status()
    with pytest.raises(RecordingBusy):
        start(runtime, 'third', room='654', creator='example.third')
    assert runtime.session_status(old['session_id'])['room_id'] == '123'
    assert runtime.session_status(queued['session_id'])['raw_copy_enabled'] is False
    a_release.set()
    b_release.set()
    wait_for(lambda: runtime.health()['active_count'] == 0)
    release.set()
    for item in (old, queued, a, b):
        wait_for(lambda: runtime.session_status(item['session_id'])['output_completed'])
    wait_for(lambda: len(runtime.journal.status()['units']) == 0)
    assert runtime.session_status(old['session_id'])['origin_slot_id'] == old['origin_slot_id']


def test_more_than_eight_lifetime_successes_remain_bounded(runtime_case):
    runtime = runtime_case.build().start_runtime()
    sessions = []
    for index in range(10):
        accepted = start(runtime, 'success' + str(index), room=str(100 + index), raw=bool(index % 2))
        sessions.append(accepted['session_id'])
        wait_for(lambda: runtime.session_status(accepted['session_id'])['output_completed'])
        wait_for(lambda: runtime.current is None)
    assert len(runtime.journal.history()) == 10
    assert not runtime.journal.status()['units']
    assert not runtime.authority._attempts
    wait_for(lambda: not runtime.captures)
    assert len(runtime.latest) <= 2 and not runtime.authority.bridges
    assert runtime.session_status(sessions[0])['output_completed']


def test_missed_h_hint_and_duplicate_room_protection(runtime_case, monkeypatch):
    case = runtime_case
    runtime = case.build(notify=lambda _: (_ for _ in ()).throw(OSError('lost H hint')))
    runtime.start_runtime()
    # Lose both the notification and the unconditional thread-exit hint.
    monkeypatch.setattr(runtime.wake, 'set', lambda: None)
    accepted = start(runtime, 'missed')
    wait_for(lambda: runtime.session_status(accepted['session_id'])['output_completed'])
    assert any(str(e) == 'lost H hint' for e in runtime.errors)
    entered, release = case.hold('capture')
    start(runtime, 'capture', room='456')
    assert entered.wait(10)
    for index in range(12):
        with pytest.raises(RecordingDuplicate):
            start(runtime, 'duplicate' + str(index), room='456', creator='example.other')
    assert len(runtime.authority.leases) <= 2
    with pytest.raises(RecordingDuplicate):
        start(runtime, 'unknown', room=None)
    release.set()
