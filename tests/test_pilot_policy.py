"""Normal policy inheritance and actual Windows pilot capture/confirmation rehearsal."""
import inspect
import json
import os
from threading import Event
from types import SimpleNamespace

import pytest

from tests import test_pilot_command as command
from tests.pilot_test_helpers import CommandProbe, generate, wait, validate
from tikrec.live import capture_live
from tikrec.pilot_composition import source_options
from tikrec.pilot_limits import PilotEnvelope


def test_normal_composition_inherits_capture_policy_without_fixture_injection(tmp_path):
    options = source_options(PilotEnvelope(tmp_path), SimpleNamespace(stop_event=Event()), 'ffprobe')
    defaults = inspect.signature(capture_live).parameters
    for name, expected in [('offline_confirmation_checks', 3),
                           ('offline_confirmation_interval', 5.0), ('backoff_seconds', 1.0)]:
        assert name not in options
        assert defaults[name].default == expected


@pytest.mark.skipif(os.name != 'nt', reason='native Windows pilot command')
@pytest.mark.parametrize('mode,sizes', [('copy', ('640x1280', '640x1280')),
                                      ('libx264', ('1280x720', '720x1280'))])
def test_connected_portrait_and_configuration_change_keep_uuid_raw_h_fifo(tmp_path, monkeypatch, mode, sizes):
    # Reuse the complete existing overlap/identity/deep-validation assertions with real geometry.
    monkeypatch.setattr(command, 'generate', lambda base: generate(base, sizes))
    command.test_actual_command_overlap_uuid_fifo_outputs_and_originals(tmp_path, mode)


@pytest.mark.skipif(os.name != 'nt', reason='native Windows pilot command')
def test_command_lone_offline_transient_same_room_and_confirmed_end(tmp_path):
    generate(tmp_path)
    probe = CommandProbe(tmp_path, 'policy')
    try:
        probe.ready()
        started = probe.start('policy', True)
        wait(lambda: (tmp_path / 'offline-unconfirmed').exists()
             or probe.client.status(started['session_id'])['output_completed'])
        assert (tmp_path / 'offline-unconfirmed').exists(), 'single offline prematurely finalized capture'
        status = probe.client.status(started['session_id'])
        assert status['active'] and not status['output_completed']
        observed = json.loads((tmp_path / 'policy-policy.json').read_text())
        assert observed['observations'] == [observed['observations'][0], 'TikTokOfflineError']
        assert observed['delays'] == [0.0, 5.0]
        (tmp_path / 'confirm-continue').write_text('allow scripted transient then same-room live')
        wait(lambda: probe.client.status(started['session_id'])['output_completed'])
        observed = json.loads((tmp_path / 'policy-policy.json').read_text())
        assert observed['delays'] == [0.0, 5.0, 1.0, 0.0, 5.0, 5.0]
        assert observed['observations'] == [observed['observations'][0], 'TikTokOfflineError',
            'TikTokResolutionTransientError', observed['observations'][0],
            'TikTokOfflineError', 'TikTokOfflineError', 'TikTokOfflineError']
        parts = probe.home / 'media' / 'policy.parts'
        records = [json.loads(line) for line in (parts / 'connections.jsonl').read_text().splitlines()]
        statuses = [row for row in records if row.get('event') == 'room_status']
        assert [row['confirmation_reached'] for row in statuses] == [False, False, False, True]
        assert [row['status'] for row in statuses] == [4, 4, 4, 4]
        assert len(list(parts.glob('part-*.flv'))) == 2
        assert b''.join(path.read_bytes() for path in sorted(parts.glob('*.raw'))) == (
            (tmp_path / 'one.flv').read_bytes() * 2)
        assert probe.client.status(started['session_id'])['session_id'] == started['session_id']
        probe.control('shutdown'); probe.finish()
        validate(parts, tmp_path)
    finally:
        command.stop_probe(probe)
