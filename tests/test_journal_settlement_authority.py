"""Live completion authority, competing finalizers and addressed terminal history."""

import copy
import os
from dataclasses import asdict
from pathlib import Path

import pytest

from tests.journal_settlement_helpers import settling, adapter_for, independent_cleanup
from tests.journal_assembly_helpers import managed_process, queue_media
from tests.capture_handoff_helpers import reserve, observations
from tikrec.journal_settlement import SettlementError
from tikrec.owned_settlement import OwnedSettlement
from tikrec.session_journal_types import SettlementProof

pytestmark = pytest.mark.skipif(os.name != 'nt', reason='Windows held success authority')


@pytest.mark.parametrize('forged', ['clone', 'failed', 'missing', 'revoked', 'installed', 'flushed', 'children'])
def test_incomplete_forged_or_revoked_live_completion_cannot_prepare(settling, monkeypatch, forged):
    adapter, _, _, _, _ = settling
    runner = adapter.coordinator
    def fault(point):
        if point != 'before_release_preparation':
            return
        cap = adapter.capability
        if forged == 'clone':
            cap.manifest = copy.copy(adapter.manifest)
        elif forged == 'failed':
            adapter.manifest.error = OSError('previous completion failed')
        elif forged == 'missing':
            monkeypatch.setattr(runner.journal, 'manifest_completion', lambda _: None)
        elif forged == 'revoked':
            adapter.cancel()
        elif forged == 'installed':
            monkeypatch.setattr(runner.manifest_owner, 'installed', False)
        elif forged == 'flushed':
            read = runner.journal.manifest_completion
            def unflushed(token):
                value = read(token)
                value['steps'][-1]['evidence']['required_flushed'] = False
                return value
            monkeypatch.setattr(runner.journal, 'manifest_completion', unflushed)
        else:
            monkeypatch.setattr(runner.children[-1]['process'], 'closed', False)
    runner._fault = fault
    with pytest.raises(SettlementError):
        adapter.run()
    assert runner.journal.settlement(runner.token) is None
    assert len(runner.journal.status()['units']) == 1
    assert runner.guard.retained


def test_competing_claim_and_generic_settlement_remain_fenced_until_terminal(settling):
    adapter, _, original, _, _ = settling
    runner, checks = adapter.coordinator, []
    def fault(point):
        if point in {'after_release_preparation', 'after_release_resource_input_0', 'before_terminal_release'}:
            store = runner.journal
            assert store.claim_owned(runner.uuid(), runner.uuid(), runner.uuid()) is None
            proof = SettlementProof(original['id'], runner.token, original['seal_hash'], 'native-exit',
                runner.guard.intent.output, 1, '1' * 64, '2' * 64)
            with pytest.raises(Exception):
                store.settle_task(runner.uuid(), original['id'], original['task']['revision'] + 1, 1, runner.token, proof)
            assert len(store.status()['units']) == 1
            with pytest.raises(Exception, match='original live release continuation'):
                store.settle_owned_success(runner.uuid(), runner.token, runner.owner, runner.revision,
                    {'cleanup_complete': True}, capability=adapter.capability)
            checks.append(point)
    runner._fault = fault
    assert adapter.run()['state'] == 'released'
    assert len(checks) == 3
    with pytest.raises(Exception):
        OwnedSettlement(adapter.manifest)
    with pytest.raises(Exception):
        adapter.capability.complete()


def test_competing_thread_cannot_borrow_the_live_terminal_call(settling, monkeypatch):
    from threading import Thread
    adapter, _, _, _, _ = settling
    runner, blocked = adapter.coordinator, []
    settle = runner.journal.settle_owned_success
    def selected(operation, *args, **options):
        def competing():
            try:
                settle(runner.uuid(), *args, **options)
            except BaseException as error:
                blocked.append(error)
        worker = Thread(target=competing)
        worker.start()
        worker.join(5)
        assert not worker.is_alive()
        return settle(operation, *args, **options)
    monkeypatch.setattr(runner.journal, 'settle_owned_success', selected)
    assert adapter.run()['returned_units'] == 1
    assert len(blocked) == 1 and 'original live release continuation' in str(blocked[0])
    assert runner.journal._read(lambda db: db.execute('SELECT count(*) FROM release_results').fetchone()[0]) == 1


def test_released_receipts_survive_new_claims_and_bound_history_inspection(settling, tmp_path, managed_process, monkeypatch):
    adapter, _, original, _, _ = settling
    runner, store = adapter.coordinator, adapter.coordinator.journal
    adapter.run()
    history = store.settlement(runner.token)
    receipts = store._read(lambda db: [dict(r) for r in db.execute('SELECT * FROM operations WHERE json_extract(result,\'$.token\')=?',
        (runner.token,))])
    # A new capture may reuse a released room; its bindings must survive old callbacks.
    bridge, _ = queue_media(runner.authority, tmp_path, name='replacement', room='123')
    next_adapter = adapter_for(runner.authority, managed_process)
    try:
        def fault(point):
            if point == 'after_claim':
                new = store.status()
                for receipt in receipts:
                    assert store.operation(receipt['id']) == receipt
                assert store.settlement(runner.token) == history
                adapter.cancel()
                assert adapter.close() and store.status() == new
        next_adapter.coordinator._fault = fault
        assert next_adapter.run()['state'] == 'released'
    finally:
        independent_cleanup(next_adapter)
    assert store.session(original['id'])['phase'] == 'completed'
    assert store.session(bridge.intent.session_id)['phase'] == 'completed'
    statements = []
    connect = store._connect
    def tracing():
        db = connect()
        db.set_trace_callback(statements.append)
        return db
    monkeypatch.setattr(store, '_connect', tracing)
    store.status()
    assert not any("SELECT * FROM attempt_owners" in sql for sql in statements)
    assert any('FROM units u JOIN tasks' in sql for sql in statements)
    plan = store._read(lambda db: [tuple(r) for r in db.execute("EXPLAIN QUERY PLAN "
        "SELECT o.token FROM units u JOIN tasks t ON t.session=u.session JOIN attempt_owners o ON o.token=t.token "
        "WHERE u.kind='task' LIMIT 9")])
    assert any('active_task_units' in r[-1] for r in plan)


@pytest.mark.parametrize('settling', [True], indirect=True)
def test_degraded_input_stays_degraded_after_success_release(settling, monkeypatch):
    import sys
    from tikrec import journal_assembly as module
    adapter, bridge, _, _, _ = settling
    build = module._build_ffmpeg_command
    def command(*args, **kwargs):
        media = build(*args, **kwargs)
        code = 'import subprocess,sys;code=subprocess.call(' + repr(media) + ");" \
            "sys.stderr.buffer.write(b'warning\\n'*4000+b'[h264 @ 0x1] corrupt slice');sys.exit(code)"
        return [str(Path(sys._base_executable)), '-c', code]
    monkeypatch.setattr(module, '_build_ffmpeg_command', command)
    assert adapter.run()['state'] == 'released'
    import json
    values = json.loads((Path(bridge.intent.parts_path) / 'session.json').read_bytes())
    assert values['finalization']['input_decode']['status'] == 'degraded'
    assert values['finalization']['input_decode']['diagnostic_count'] > 0
    assert adapter.coordinator.journal.validation(adapter.coordinator.token)['evidence']['report']['passed']
