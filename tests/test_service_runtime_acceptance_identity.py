"""Independent automatic launch-ack loss and original identity across slot reuse."""

import os
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from threading import Event, Thread
from uuid import uuid4

import pytest

pytestmark = pytest.mark.skipif(os.name != 'nt', reason='native Windows runtime')

from tests.service_runtime_helpers import runtime_case, managed_process, start, wait_for, hashes, preserved
from tikrec.admission import RecordingAdmission
from tikrec.automation import AutomationCoordinator
from tikrec.automation_state import AutomationStateStore
from tikrec.service_runtime_automation import claim_id


@pytest.mark.parametrize('raw', [False, True])
def test_automatic_started_thread_ack_loss_survives_policy_change_and_slot_reuse(runtime_case, tmp_path, raw):
    case = runtime_case
    first_error = OSError('independent automatic capture startup acknowledgement lost')
    created = []

    class LostAcknowledgement(Thread):
        def start(self):
            super().start()
            raise first_error

    def factory(**options):
        if options['name'].startswith('tikrec-isolated-capture') and not created:
            thread = LostAcknowledgement(**options)
            created.append(thread)
            return thread
        return Thread(**options)

    entered, release = Event(), Event()
    case.releases.append(release)
    runtime = case.build(thread_factory=factory).start_runtime()

    def fault(point):
        if point == 'after_media_plan':
            entered.set()
            assert release.wait(90)

    case.fault = fault
    admission = RecordingAdmission(runtime.root, runtime.health, storage_status=runtime.storage,
        clock=lambda: datetime(2026, 10, 8, 12))
    store = AutomationStateStore(tmp_path / 'review-automation.json')
    automation = AutomationCoordinator(runtime, admission, store,
        automatic_raw_copy_creators=('example.creator',) if raw else ())
    runtime.automation = automation
    cycle = {'cycle_count': 1, 'creators': [
        {'creator': 'example.creator', 'state': 'live', 'room_id': '123'}]}
    automation.cycle_completed(cycle)
    claim = store.load().pending_claim
    assert claim is not None and runtime.errors[0] is first_error
    assert entered.wait(30)
    receipt = runtime.journal.automatic_receipt(claim_id(claim))
    sid = receipt['session']
    original = runtime.session_status(sid)
    row = runtime.journal.session(sid)
    token = runtime.current.coordinator.token
    before = hashes(Path(original['parts_directory']), runtime.current)
    assert original['creator'] == claim.creator and original['room_id'] == claim.room_id
    assert original['output_path'] == claim.output_path
    assert original['parts_directory'] == claim.parts_directory
    assert original['raw_copy_enabled'] is raw and not original['output_completed']
    assert created[0].ident is not None
    replacements = []
    for name, room in [('replacement-a', '456'), ('replacement-b', '789')]:
        ready, _ = case.hold(name)
        replacements.append(start(runtime, name, room=room, raw=not raw,
            creator='example.creator' if name == 'replacement-a' else 'example.other'))
        assert ready.wait(10)
    assert replacements[0]['origin_slot_id'] == original['origin_slot_id']
    assert replacements[0]['generation'] > original['generation']
    # A fresh coordinator has a different raw preference, but reconciliation uses
    # the original durable acceptance rather than today's slot/policy snapshot.
    automation.stop()
    restarted_coordinator = AutomationCoordinator(runtime, admission, store,
        automatic_raw_copy_creators=() if raw else ('example.creator',))
    runtime.automation = restarted_coordinator
    assert store.load().pending_claim is None
    assert store.load().consumed() == {'example.creator': '123'}
    assert runtime.reconcile_automatic_claim(claim) is True
    for changed in (
        replace(claim, creator='example.changed'), replace(claim, room_id='987'),
        replace(claim, previous_session_id=str(uuid4())),
        replace(claim, output_path=str(runtime.root / 'different.mp4'),
                parts_directory=str(runtime.root / 'different.parts')),
    ):
        assert runtime.reconcile_automatic_claim(changed) is False
    restarted_coordinator.cycle_completed({**cycle, 'cycle_count': 2})
    assert len(runtime.journal.history()) == 3
    assert runtime.stop(sid)['stop_result'] == 'capture_already_closed'
    assert not runtime.capture_callback(sid, original['generation'], 'state', 'failed')
    assert all(not runtime.captures[item['session_id']]['bridge'].stop_event.is_set() for item in replacements)
    release.set()
    wait_for(lambda: runtime.session_status(sid)['output_completed'])
    preserved(before, token)
    current = runtime.journal.session(sid)
    assert all(current[key] == row[key] for key in ('intent', 'seal', 'seal_hash', 'generation', 'origin_slot'))
    assert runtime.journal.automatic_receipt(claim_id(claim)) == receipt
    for name in ('replacement-a', 'replacement-b'):
        case.holds[name][1].set()
    wait_for(lambda: not runtime.journal.status()['units'])
    assert runtime.shutdown()['complete']
    reopened = case.build().start_runtime()
    assert reopened.reconcile_automatic_claim(claim) is True
    assert reopened.session_status(sid)['raw_copy_enabled'] is raw
    assert reopened.journal.automatic_receipt(claim_id(claim)) == receipt
    assert reopened.journal._read(lambda db: db.execute('SELECT count(*) FROM release_results').fetchone()[0]) == 3
    assert reopened.shutdown()['complete']
    assert not created[0].is_alive()
