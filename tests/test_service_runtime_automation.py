"""Existing admission/automation driven through actual accepted capture and H."""

import os
from datetime import datetime
from threading import Event

import pytest

pytestmark = pytest.mark.skipif(os.name != 'nt', reason='native Windows runtime')

from tests.service_runtime_helpers import runtime_case, managed_process, start, wait_for
from tikrec.admission import RecordingAdmission
from tikrec.automation import AutomationCoordinator
from tikrec.automation_state import AutomationStateStore
from tikrec.service_runtime_automation import claim_id


def cycle(number, room='123', state='live'):
    """One trustworthy offline fixture monitoring cycle."""
    return {'cycle_count': number, 'creators': [{'creator': 'example.creator',
        'state': state, 'room_id': room if state == 'live' else None}]}


@pytest.mark.parametrize('raw', [False, True])
def test_automatic_same_creator_new_room_during_old_finalization(runtime_case, tmp_path, raw):
    case = runtime_case
    entered, release = Event(), Event()
    case.releases.append(release)
    def fault(point):
        if point == 'after_media_plan':
            entered.set()
            assert release.wait(45)
    case.fault = fault
    runtime = case.build().start_runtime()
    old = start(runtime, 'manual-old')
    assert entered.wait(30)
    admission = RecordingAdmission(runtime.root, runtime.health, storage_status=runtime.storage,
        clock=lambda: datetime(2026, 10, 7, 12))
    store = AutomationStateStore(tmp_path / 'automation.json')
    automation = AutomationCoordinator(runtime, admission, store,
        automatic_raw_copy_creators=('example.creator',) if raw else ())
    runtime.automation = automation
    automation.cycle_completed(cycle(1, '456'))
    accepted = automation.snapshot(cycle(1, '456'))['automation']['started_recordings'][0]
    sid = accepted['session_id']
    wait_for(lambda: runtime.journal.session(sid)['phase'] == 'queued')
    assert store.load().consumed()['example.creator'] == '456'
    assert runtime.session_status(sid)['raw_copy_enabled'] is raw
    assert runtime.session_status(old['session_id'])['room_id'] == '123'
    automation.cycle_completed(cycle(2, '456'))
    assert len(runtime.journal.history()) == 2
    release.set()
    wait_for(lambda: runtime.session_status(sid)['output_completed'])


def test_acceptance_survives_h_and_replacement_before_promotion(runtime_case, tmp_path, monkeypatch):
    case = runtime_case
    runtime = case.build().start_runtime()
    admission = RecordingAdmission(runtime.root, runtime.health, storage_status=runtime.storage,
        clock=lambda: datetime(2026, 10, 7, 12))
    store = AutomationStateStore(tmp_path / 'automation.json')
    original = store.save
    saved = []
    def failed_promotion(state):
        if state.pending_claim is not None:
            saved.append(state.pending_claim)
            return original(state)
        if saved:
            receipt_id = claim_id(saved[0])
            receipt = runtime.journal.automatic_receipt(receipt_id)
            wait_for(lambda: runtime.journal.session(receipt['session'])['phase'] in {'queued', 'running', 'completed'})
            replacement = start(runtime, 'replacement', room='456')
            saved.append(replacement)
            raise OSError('promotion acknowledgement lost')
        return original(state)
    monkeypatch.setattr(store, 'save', failed_promotion)
    automation = AutomationCoordinator(runtime, admission, store)
    automation.cycle_completed(cycle(1))
    claim = store.load().pending_claim
    assert claim is not None and len(saved) == 2
    accepted = runtime.journal.automatic_receipt(claim_id(claim))
    assert accepted['session'] != saved[1]['session_id']
    monkeypatch.setattr(store, 'save', original)
    reconciled = AutomationCoordinator(runtime, admission, store)
    runtime.automation = reconciled
    assert store.load().pending_claim is None
    assert store.load().consumed()['example.creator'] == '123'
    assert runtime.reconcile_automatic_claim(claim) is True
    wait_for(lambda: runtime.session_status(saved[1]['session_id'])['output_completed'])
    assert runtime.reconcile_automatic_claim(claim) is True


def test_shutdown_fences_late_automation_and_current_callbacks(runtime_case, tmp_path):
    case = runtime_case
    runtime = case.build().start_runtime()
    admission = RecordingAdmission(runtime.root, runtime.health, storage_status=runtime.storage)
    store = AutomationStateStore(tmp_path / 'automation.json')
    automation = AutomationCoordinator(runtime, admission, store)
    runtime.automation = automation
    assert runtime.shutdown()['complete']
    automation.cycle_completed(cycle(1))
    assert not runtime.journal.history()
    assert runtime.health()['available_slots'] == 0
