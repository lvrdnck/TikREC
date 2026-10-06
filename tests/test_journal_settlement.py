"""The new connected success path returns capacity only after actual local cleanup."""

import hashlib
import json
import os
from pathlib import Path

import pytest

from tests.journal_settlement_helpers import settling, adapter_for, independent_cleanup
from tests.journal_assembly_helpers import managed_process, queue_media

pytestmark = pytest.mark.skipif(os.name != 'nt', reason='native Windows lifecycle')


@pytest.mark.parametrize('settling', [False, True, 'interrupted'], indirect=True)
def test_connected_success_releases_exact_accounting_and_preserves_media(settling):
    adapter, bridge, original, before, raw = settling
    result = adapter.run()
    runner = adapter.coordinator
    store = runner.journal
    assert result['state'] == 'released' and result['returned_units'] == 1
    current = store.session(original['id'])
    assert current['phase'] == current['task']['state'] == 'completed'
    assert current['artifacts'] == current['rooms'] == []
    assert store.status()['units'] == store.status()['tasks'] == []
    assert runner.closed and adapter.cleanup_evidence()['cleanup_complete']
    runner.authority.assert_held()
    assert runner.authority.media.handle is not None
    assert store.automatic_receipt(original['automatic_claim'])['session'] == original['id']
    record = store.settlement(runner.token)
    assert record['state'] == 'released' and record['result']['evidence']['cleanup_complete']
    assert store.owned_attempt(runner.token)['state'] == 'revoked'
    candidate = store.scratch(runner.token)['candidate']
    output = Path(bridge.intent.output_path)
    assert hashlib.sha256(output.read_bytes()).hexdigest() == candidate['sha256']
    values, old = json.loads((Path(bridge.intent.parts_path) / 'session.json').read_bytes()), json.loads(raw)
    for key in old.keys() - {'finalization', 'media'}:
        assert values[key] == old[key]
    assert values['finalization']['status'] == 'completed'
    if not old['interrupted']:
        copy = adapter.manifest.publication.validation.assembly.plan.stream_copy
        assert candidate['sha256'] == ('564dc75486b06c55dfe12ab6acaeccd3eeaaba46f1d53374943323a8f9ee24af'
            if copy else '675817cf334dbce51ee8efd41559f3ec1ead86ca9deb9648caa7363734326d6c')
        assert values['media'] == {'video_codec': 'h264', 'audio_codec': 'aac', 'width': 64 if copy else 80, 'height': 64}
        assert values['finalization']['input_decode']['status'] == ('not_checked' if copy else 'clean')
    assert candidate['publication'] == 'unpublished' and candidate['validation'] == 'not_checked'
    assert adapter.close() and adapter.cancel() is None
    assert store.settlement(runner.token) == record
    with pytest.raises(Exception):
        adapter.run()


def test_terminal_release_evidence_and_identity_are_immutable(settling):
    import sqlite3
    adapter, _, original, _, _ = settling
    adapter.run()
    store = adapter.coordinator.journal
    before = store.settlement(adapter.coordinator.token)
    with sqlite3.connect(store.path) as db:
        for sql in ["UPDATE release_preparations SET binding='{}'", 'DELETE FROM release_preparations',
            "UPDATE release_cleanups SET evidence='{}'", 'DELETE FROM release_cleanups',
            "UPDATE release_results SET evidence='{}'", 'DELETE FROM release_results',
            "UPDATE tasks SET state='running'", "UPDATE attempts SET state='running'",
            "UPDATE sessions SET phase='running'", 'DELETE FROM attempt_owners']:
            with pytest.raises(sqlite3.IntegrityError):
                db.execute(sql)
    assert store.settlement(adapter.coordinator.token) == before
    assert store.session(original['id'])['phase'] == 'completed'


def test_more_than_eight_successes_and_reused_capture_bindings(settling, tmp_path, managed_process):
    adapter, bridge, _, _, _ = settling
    owner = adapter.coordinator.authority
    adapters, receipts = [adapter], []
    try:
        for index in range(10):
            if index:
                bridge, _ = queue_media(owner, tmp_path, name=f'next{index}', room=str(200 + index))
                adapter = adapter_for(owner, managed_process)
                adapters.append(adapter)
            assert adapter.run()['returned_units'] == 1
            token = adapter.coordinator.token
            receipts.append((token, owner.journal.settlement(token)))
            assert owner.journal.status()['units'] == []
            for old_token, receipt in receipts:
                assert owner.journal.settlement(old_token) == receipt
                assert owner.journal.owned_attempt(old_token)['state'] == 'revoked'
        assert len(owner.journal.history()) == 10
        assert owner.journal.status()['bindings'][0]['generation'] == 10
    finally:
        for item in adapters[1:]:
            independent_cleanup(item)
