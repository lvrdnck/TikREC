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
