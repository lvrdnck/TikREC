"""Original finalizer cancellation and live-capture shutdown, without unsafe refunds."""
import json
import os
import shutil
import subprocess

import pytest

from tests.operational_helpers import Probe
from tests.pilot_test_helpers import generate, wait
from tikrec.session_journal import SessionJournal

pytestmark = pytest.mark.skipif(os.name != 'nt', reason='native Windows pressure controls')


@pytest.mark.parametrize('pressure', ['low', 'unknown'])
def test_pressure_cancels_only_owned_finalizer_and_preserves_capture_policy(tmp_path, pressure):
    generate(tmp_path)
    probe = Probe(tmp_path, 'hold').launch(init=True).launch()
    try:
        probe.ready(); old = probe.start('old', True)
        wait(lambda: (tmp_path / 'finalizer-held').exists())
        new = probe.start('writer', True)
        wait(lambda: (tmp_path / 'source-held').exists())
        # Active parts retain their temporary name until close; use live writer evidence.
        assert probe.client.status(new['session_id'])['bytes_written'] > 13
        (tmp_path / 'free.txt').write_text('unknown' if pressure == 'unknown' else str(2 * 1024**3))
        journal = SessionJournal(probe.home / 'state' / 'sessions.sqlite3', probe.catalog)
        wait(lambda: journal.owned_attempt(journal.session(old['session_id'])['task']['token'])['state'] == 'revoked')
        if pressure == 'low':
            assert probe.client.status(new['session_id'])['active']
        else:
            wait(lambda: not probe.client.status(new['session_id'])['active'])
            assert probe.client.status(new['session_id'])['stop_requested']
        (tmp_path / 'release-finalizer').touch()
        wait(lambda: probe.client.health()['finalization']['paused_reason'] == 'finalizer_needs_attention')
        assert not probe.client.status(old['session_id'])['output_completed']
        assert len(journal.status()['units']) == 2
        # Restored space cannot retry the consumed original attempt.
        (tmp_path / 'free.txt').write_text(str(30 * 1024**3))
        assert probe.client.status(old['session_id'])['finalization_state'] == 'running'
        probe.control(); probe.finish(3)
        assert len(journal.status()['units']) == 2
        assert not (probe.home / 'media' / 'old.mp4').exists()
    finally:
        probe.stop()


def test_shutdown_with_original_capture_and_active_finalizer(tmp_path):
    generate(tmp_path)
    probe = Probe(tmp_path, 'hold').launch(init=True).launch()
    try:
        probe.ready(); old = probe.start('old', True)
        wait(lambda: (tmp_path / 'finalizer-held').exists())
        new = probe.start('writer', True)
        wait(lambda: (tmp_path / 'source-held').exists())
        probe.control()
        journal = SessionJournal(probe.home / 'state' / 'sessions.sqlite3', probe.catalog)
        wait(lambda: journal.session(new['session_id'])['stop'])
        (tmp_path / 'release-finalizer').touch()
        probe.finish()
        assert journal.session(old['session_id'])['phase'] == 'completed'
        assert journal.session(new['session_id'])['stop']
        assert journal.session(new['session_id'])['task']['state'] == 'queued'
        assert len(journal.status()['units']) == 1
    finally:
        probe.stop()


def test_actual_dynamic_writer_budget_zero_exit_never_publishes_truncated_candidate(tmp_path):
    subprocess.run([shutil.which('ffmpeg'), '-v', 'error', '-f', 'lavfi', '-i',
        'testsrc2=size=1280x720:rate=30', '-f', 'lavfi', '-i', 'sine=sample_rate=44100',
        '-t', '12', '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '0', '-g', '1',
        '-c:a', 'aac', '-f', 'flv', str(tmp_path / 'large.flv')],
        check=True, capture_output=True, timeout=60)
    assert (tmp_path / 'large.flv').stat().st_size > 16 * 1024**2
    probe = Probe(tmp_path, 'budget').launch(init=True).launch()
    try:
        probe.ready(); value = probe.start('budget', True); sid = value['session_id']
        wait(lambda: probe.client.health()['finalization']['paused_reason'] == 'candidate_budget_needs_attention', seconds=180)
        assert not probe.client.status(sid)['output_completed']
        journal = SessionJournal(probe.home / 'state' / 'sessions.sqlite3', probe.catalog)
        token = journal.session(sid)['task']['token']
        assert journal.scratch(token)['candidate']['size'] >= 14 * 1024**2
        assert journal.validation(token) is None
        assert not (probe.home / 'media' / 'budget.mp4').exists()
        probe.control(); probe.finish(3)
        assert len(journal.status()['units']) == 1
        assert journal.session(sid)['task']['state'] == 'running'
    finally:
        probe.stop()
