"""Original pre-H refusal must retire locally without completing durable evidence."""
import hashlib
import json
import os
from pathlib import Path

import pytest

from tests.pilot_test_helpers import CommandProbe, generate, wait
from tikrec.session_journal import SessionJournal

pytestmark = pytest.mark.skipif(os.name != 'nt', reason='native Windows refusal retirement')


def media_hashes(root):
    """Freeze original source/raw/control bytes, excluding active lock contents."""
    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*') if p.is_file() and p.name != '.tikrec-lifecycle.lock'}


@pytest.mark.parametrize('size', ['1922x1080', '1280x1280', 'invalid-header'])
def test_quiescent_preconfiguration_refusal_exits_without_h_or_refund(tmp_path, size):
    """Real refused AVC keeps its original evidence/unit/binding through normal exit."""
    generate(tmp_path, ('64x64' if size == 'invalid-header' else size, '64x64'))
    if size == 'invalid-header':
        source = tmp_path / 'one.flv'
        source.write_bytes(b'BAD' + source.read_bytes()[3:])  # Corrupt only a newly generated fixture.
    sources = media_hashes(tmp_path)
    probe = CommandProbe(tmp_path, 'reopen', module='tests.pilot_refusal_probe')
    sid = None
    try:
        ready = probe.ready()
        sid = probe.start('oversized', True)['session_id']
        wait(lambda: any(e['event'] == 'shutdown' for e in probe.events()))
        shutdown = [e for e in probe.events() if e['event'] == 'shutdown'][-1]
        assert shutdown['complete'] and shutdown['authority_released'], shutdown
        assert shutdown['captures_joined'] and shutdown['finalizer_joined']
        probe.finish(expected=3)
        owners = json.loads((tmp_path / 'refusal-owners.jsonl').read_text().splitlines()[-1])
        before, after = owners['before'], owners['after']
        assert before['media'] == after['media']
        assert before['durable'] == after['durable']
        assert all(not g for g in after['authority_native_retained'])
        original = after['captures'][sid]
        assert original['refusal_retired'] and not original['lease_native_retained']
        assert original['source_counts'][0] == original['source_counts'][1] > 0
        assert original['writer_openings'] == 0 and all(original['raw_closed'])
        assert not any(original['raw_guards'])
        assert not after['worker_alive'] and not after['connections_owned']
        assert after['requests_owned'] == 0 and after['listener_fd'] == -1
        journal = SessionJournal(Path(ready['catalog']), probe.catalog)
        row, status = journal.session(sid), journal.status()
        assert row['phase'] == 'closing' and row['seal'] is None and row['task'] is None
        assert bool(row['stop']) == (size != 'invalid-header') and row['intent']['raw_copy']
        assert len(status['units']) == 1
        assert any(b['session'] == sid for b in status['bindings'])
        assert not (probe.home / 'media' / 'oversized.mp4').exists()
        raw = sorted((probe.home / 'media' / 'oversized.parts').glob('*.raw'))
        assert raw and b''.join(p.read_bytes() for p in raw) == (
            tmp_path / 'one.flv').read_bytes()[:sum(p.stat().st_size for p in raw)]
        assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest() == sha for p, sha in sources.items())
        (tmp_path / 'refusal-retirement-proof.json').write_text(json.dumps({
            'session': sid, 'row': row, 'status': status, 'shutdown': shutdown,
            'preserved_media': media_hashes(probe.home / 'media'),
            'owners': owners, 'product_retirement': True, 'forced_fixture_cleanup': False}, indent=2))
        # Only this corrected, newly fingerprint-bound fixture is reopened; old homes stay untouched.
        preserved = media_hashes(probe.home / 'media')
        reopened_base = tmp_path / 'reopened'
        reopened_base.mkdir()
        reopened = CommandProbe(reopened_base, 'reopen', home=probe.home,
            catalog=probe.catalog, reopen=True, module='tests.pilot_refusal_probe')
        reopened.finish(expected=3)
        assert journal.session(sid) == row and journal.status() == status
        assert media_hashes(probe.home / 'media') == preserved
        assert any(e['event'] == 'stop_condition' and e['reason'] ==
                   'pilot_unsupported_or_uncertain_state' for e in reopened.events())
        reopen_owners = json.loads((reopened_base / 'refusal-owners.jsonl').read_text().splitlines()[-1])
        assert reopen_owners['after']['captures'] == {} and reopen_owners['complete']
    finally:
        if probe.process.poll() is None:
            # The intentionally failing unchanged baseline cannot retire itself;
            # this exact disposable intervention is never positive exit evidence.
            (tmp_path / 'failed-regression-fixture-intervention.json').write_text(json.dumps({
                'pid': probe.process.pid, 'command': probe.args, 'session': sid,
                'reason': 'failed regression fixture only; NOT confirmed product retirement'}))
            probe.process.terminate()
            probe.process.wait(timeout=15)
        probe.stream.close()


@pytest.mark.parametrize('mode', ['refusal-lease-close', 'refusal-raw-close', 'refusal-arrival-close'])
def test_actual_refusal_native_close_fault_requires_repair_and_explicit_retry(tmp_path, mode):
    """Python-closed originals stay reachable until exact native retirement is confirmed."""
    generate(tmp_path, ('1922x1080', '64x64'))
    probe = CommandProbe(tmp_path, mode, module='tests.pilot_refusal_probe')
    try:
        ready = probe.ready()
        sid = probe.start('oversized', True)['session_id']
        wait(lambda: any(e['event'] == 'shutdown' for e in probe.events()))
        first = [e for e in probe.events() if e['event'] == 'shutdown'][-1]
        assert not first['complete'] and first['captures_joined'] and first['finalizer_joined']
        assert probe.process.poll() is None
        journal = SessionJournal(Path(ready['catalog']), probe.catalog)
        row, status = journal.session(sid), journal.status()
        hashes = media_hashes(probe.home / 'media')
        initial = json.loads((tmp_path / 'refusal-owners.jsonl').read_text().splitlines()[-1])
        capture = initial['after']['captures'][sid]
        assert capture['authority_bridge'] and capture['authority_lease']
        assert capture['lease_native_retained'] or any(capture['raw_guards'])
        assert capture['handle_closed'] if mode == 'refusal-lease-close' else all(capture['raw_closed'])
        # A second request without repairing the native fault is still truthfully incomplete.
        count = len([e for e in probe.events() if e['event'] == 'shutdown'])
        probe.control('cleanup')
        wait(lambda: len([e for e in probe.events() if e['event'] == 'shutdown']) > count)
        assert not [e for e in probe.events() if e['event'] == 'shutdown'][-1]['complete']
        assert journal.session(sid) == row and journal.status() == status
        (tmp_path / 'repair').write_text('remove exact generated native protection')
        probe.control('cleanup')
        probe.finish(expected=3)
        final = json.loads((tmp_path / 'refusal-owners.jsonl').read_text().splitlines()[-1])
        assert final['complete'] and not any(final['after']['authority_native_retained'])
        closed = final['after']['captures'][sid]
        assert not closed['lease_native_retained'] and not any(closed['raw_guards'])
        assert closed['lease_errors'] if mode == 'refusal-lease-close' else closed['raw_errors']
        assert journal.session(sid) == row and journal.status() == status
        assert media_hashes(probe.home / 'media') == hashes
        (tmp_path / 'refusal-close-retry-proof.json').write_text(json.dumps({
            'row': row, 'status': status, 'preserved_media': hashes,
            'initial': initial, 'final': final, 'exit': probe.process.returncode}, indent=2))
    finally:
        if probe.process.poll() is None:
            # Repair only this disposable fault, then let product cleanup own its exit.
            (tmp_path / 'repair').write_text('test failure: repair original generated fault')
            probe.control('cleanup')
            probe.process.wait(timeout=30)
        probe.stream.close()


def test_manual_shutdown_after_refusal_is_nonzero_before_supervisor_observation(tmp_path):
    """A requested stop cannot relabel a proved original refusal as a healthy exit."""
    generate(tmp_path, ('1922x1080', '64x64'))
    probe = CommandProbe(tmp_path, 'reopen', module='tests.pilot_refusal_probe')
    try:
        ready = probe.ready()
        sid = probe.start('oversized', True)['session_id']
        journal = SessionJournal(Path(ready['catalog']), probe.catalog)
        wait(lambda: (tmp_path / (sid + '-capture-retired')).exists(), seconds=5)
        assert not any(e['event'] == 'stop_condition' for e in probe.events())
        row, status, original = journal.session(sid), journal.status(), media_hashes(probe.home / 'media')
        probe.control('shutdown')
        probe.finish(expected=3)
        assert not any(e['event'] == 'stop_condition' for e in probe.events())
        assert journal.session(sid) == row and journal.status() == status
        assert media_hashes(probe.home / 'media') == original
        owners = json.loads((tmp_path / 'refusal-owners.jsonl').read_text().splitlines()[-1])
        assert owners['complete'] and owners['after']['captures'][sid]['refusal_retired']
        (tmp_path / 'manual-refusal-stop-proof.json').write_text(json.dumps({
            'owners': owners, 'row': row, 'status': status,
            'exit': probe.process.returncode, 'supervisor_stop_condition': False}, indent=2))
    finally:
        if probe.process.poll() is None:
            probe.control('shutdown')
            probe.process.wait(timeout=30)
        probe.stream.close()
