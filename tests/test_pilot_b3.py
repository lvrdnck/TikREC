"""Fresh B3 operator probes; fixture termination never proves product retirement."""
import hashlib
import json
import os
from pathlib import Path

import pytest

from tests.pilot_test_helpers import CommandProbe, generate, wait, validate
from tests.test_pilot_command import stop_probe
from tikrec.remote import RemoteClient, RemoteError
from tikrec.session_journal import SessionJournal

pytestmark = pytest.mark.skipif(os.name != 'nt', reason='native Windows pilot')


def hashes(root):
    """Preserve every generated media artifact, including raw and control evidence."""
    # Active Windows byte-range lock contents are neither media nor durable proof.
    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*') if p.is_file() and p.name != '.tikrec-lifecycle.lock'}


def test_command_authentication_and_lifetime_survive_completed_reopen(tmp_path):
    """Eight real successes never reset lifetime permission at slot reuse/reopen."""
    generate(tmp_path)
    probe = CommandProbe(tmp_path, 'reopen')
    try:
        ready = probe.ready()
        endpoint = 'http://127.0.0.1:' + str(ready['port'])
        for token in (None, 'wrong-generated-secret'):
            with pytest.raises(RemoteError, match='401'):
                RemoteClient(endpoint, token=token).health()
        with pytest.raises(RemoteError):
            probe.client.start('https://www.tiktok.com/@fixture.outside/live',
                               str(tmp_path / 'outside.mp4'))
        journal = SessionJournal(Path(ready['catalog']), probe.catalog)
        assert not journal.history() and not (tmp_path / 'outside.mp4').exists()
        identities = []
        for index in range(8):
            value = probe.start('lifetime' + str(index), raw=index == 0)
            identities.append(value['session_id'])
            wait(lambda: probe.client.status(value['session_id'])['output_completed'])
            assert not journal.status()['units']
        assert len(set(identities)) == 8
        health = probe.client.health()
        assert health['active_count'] == 0 and health['available_slots'] == 2
        assert not health['admission_available']
        assert health['admission_reason'] == 'pilot_lifetime_limit'
        with pytest.raises(RemoteError, match='409'):
            probe.start('ninth')
        assert len(journal.history()) == 8
        probe.control('shutdown')
        probe.finish()
        before = hashes(probe.home / 'media')
        second = CommandProbe(tmp_path, 'reopen', home=probe.home,
                              catalog=probe.catalog, reopen=True)
        try:
            second.ready()
            assert all(second.client.status(sid)['output_completed'] for sid in identities)
            assert second.client.health()['admission_reason'] == 'pilot_lifetime_limit'
            with pytest.raises(RemoteError, match='409'):
                second.start('ninth-after-reopen')
            assert len(journal.history()) == 8 and not journal.status()['units']
            second.control('shutdown')
            second.finish()
            assert hashes(probe.home / 'media') == before
        finally:
            stop_probe(second)
        validate(probe.home / 'media' / 'lifetime0.parts', tmp_path)
    finally:
        stop_probe(probe)


def test_command_preconfiguration_refusal_preserves_incomplete_owners(tmp_path):
    """Actual oversized AVC refusal is retained, never safe-exit/rollback evidence."""
    generate(tmp_path, ('1922x1080', '64x64'))
    source = hashes(tmp_path)
    probe = CommandProbe(tmp_path, 'reopen', module='tests.pilot_b3_probe')
    sid = None
    try:
        ready = probe.ready()
        value = probe.start('oversized', True)
        sid = value['session_id']
        wait(lambda: any(e['event'] == 'shutdown' for e in probe.events()))
        shutdown = [e for e in probe.events() if e['event'] == 'shutdown'][-1]
        assert not shutdown['complete'] and not shutdown['authority_released']
        assert shutdown['captures_joined'] and shutdown['finalizer_joined']
        assert probe.process.poll() is None
        journal = SessionJournal(Path(ready['catalog']), probe.catalog)
        row = journal.session(sid)
        status = journal.status()
        assert row['phase'] == 'closing' and row['seal'] is None and row['task'] is None
        assert row['stop'] and row['intent']['raw_copy']
        assert len(status['units']) == 1
        assert any(b['session'] == sid for b in status['bindings'])
        assert not (probe.home / 'media' / 'oversized.mp4').exists()
        before = hashes(probe.home)
        raw = sorted((probe.home / 'media' / 'oversized.parts').glob('*.raw'))
        assert raw and b''.join(p.read_bytes() for p in raw) == (
            tmp_path / 'one.flv').read_bytes()[:sum(p.stat().st_size for p in raw)]
        count = len([e for e in probe.events() if e['event'] == 'shutdown'])
        probe.control('cleanup')
        wait(lambda: len([e for e in probe.events() if e['event'] == 'shutdown']) > count)
        last = [e for e in probe.events() if e['event'] == 'shutdown'][-1]
        assert not last['complete'] and not last['authority_released']
        assert probe.process.poll() is None and journal.session(sid) == row
        observations = [json.loads(line) for line in (
            tmp_path / 'owner-observations.jsonl').read_text().splitlines()]
        owner = observations[-1]
        capture = owner['captures'][sid]
        assert capture['done'] and not capture['thread_alive'] and not capture['fence_active']
        assert capture['authority_bridge'] and capture['authority_lease']
        assert not capture['lease_closed'] and not capture['handle_closed']
        assert not owner['connections_owned'] and not owner['worker_alive']
        assert owner['requests_owned'] == 0 and owner['listener_fd'] == -1
        assert not owner['authority_closed']
        # The control nonce is the only expected write during explicit cleanup.
        after = hashes(probe.home)
        assert all(after[path] == sha for path, sha in before.items()
                   if Path(path).name != 'control.json')
        assert all(hashlib.sha256(Path(path).read_bytes()).hexdigest() == sha
                   for path, sha in source.items())
        (tmp_path / 'early-refusal-proof.json').write_text(json.dumps({
            'session': sid, 'row': row, 'status': status, 'shutdown': shutdown,
            'cleanup': last, 'preserved_hashes': after,
            'product_retirement': False, 'forced_fixture_cleanup': True}, indent=2))
    finally:
        # This disposable fixture cannot use finish(): product cleanup is incomplete.
        # Terminate only the exact subprocess object launched above, recording the
        # intervention separately. This is explicitly excluded from operator steps.
        if probe.process.poll() is None:
            (tmp_path / 'forced-fixture-cleanup.json').write_text(json.dumps({
                'pid': probe.process.pid, 'command': probe.args, 'session': sid,
                'reason': 'retained pre-configuration lease; NOT product retirement'}))
            probe.process.terminate()
            probe.process.wait(timeout=15)
        probe.stream.close()
