"""Additional command-level startup, queued restart and capped-writer controls."""
import hashlib
import json
import os
import shutil
import socket
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(os.name != 'nt', reason='native Windows pilot')
from tests.pilot_test_helpers import CommandProbe, generate, wait, validate
from tests.test_pilot_command import stop_probe
from tikrec.session_journal import SessionJournal


@pytest.mark.parametrize('failure', ['low-space', 'occupied-listener'])
def test_actual_command_startup_refusal_retirement_and_preservation(tmp_path, failure):
    generate(tmp_path)
    listener = socket.socket()
    listener.bind(('127.0.0.1', 0)); listener.listen()
    if failure == 'low-space':
        (tmp_path / 'free.txt').write_text('0')
    probe = CommandProbe(tmp_path, port=listener.getsockname()[1] if failure == 'occupied-listener' else 0)
    try:
        events = probe.finish(2)
        assert any(e['event'] == 'failure' for e in probe.events())
        if failure == 'low-space':
            assert not probe.home.exists() and not events
        else:
            assert events[-1]['complete'] and events[-1]['primary_type'] in {'OSError', 'PermissionError'}
            assert (probe.home / 'pilot.json').exists()
            assert not SessionJournal(probe.home / 'state' / 'sessions.sqlite3', probe.catalog).history()
    finally:
        listener.close(); stop_probe(probe)


def test_actual_command_queued_restart_does_not_drain_or_replay_shutdown(tmp_path):
    generate(tmp_path); first = CommandProbe(tmp_path, 'queued')
    try:
        first.ready(); old = first.start('old', True)
        wait(lambda: (tmp_path / 'held').exists())
        next_one = first.start('later')
        wait(lambda: first.client.status(next_one['session_id'])['finalization_state'] == 'queued')
        journal = SessionJournal(first.home / 'state' / 'sessions.sqlite3', first.catalog)
        immutable = journal.session(next_one['session_id'])['seal']
        first.control('shutdown')
        wait(lambda: (tmp_path / 'stopping').exists())
        (tmp_path / 'release').write_text('release during original bounded shutdown grace')
        first.finish()
        assert journal.session(old['session_id'])['phase'] == 'completed'
        assert journal.session(next_one['session_id'])['phase'] == 'queued'
        assert len(journal.status()['units']) == 1
        second = CommandProbe(tmp_path, 'reopen', home=first.home, catalog=first.catalog, reopen=True)
        try:
            second.ready()
            wait(lambda: second.client.status(next_one['session_id'])['output_completed'])
            assert journal.session(next_one['session_id'])['seal'] == immutable
            assert not journal.status()['units']
            second.control('shutdown'); second.finish()
            validate(first.home / 'media' / 'later.parts', tmp_path)
        finally:
            stop_probe(second)
    finally:
        stop_probe(first)


def test_actual_command_capped_writer_never_reports_truncated_output_complete(tmp_path):
    generate(tmp_path)
    (tmp_path / 'one.flv').unlink()  # Generated disposable fixture only.
    subprocess.run([shutil.which('ffmpeg'), '-v', 'error', '-f', 'lavfi', '-i',
        'testsrc2=size=320x240:rate=30', '-f', 'lavfi', '-i', 'sine=sample_rate=44100',
        '-t', '5', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-g', '30', '-c:a', 'aac',
        '-f', 'flv', str(tmp_path / 'one.flv')], check=True, capture_output=True, timeout=30)
    original = hashlib.sha256((tmp_path / 'one.flv').read_bytes()).hexdigest()
    probe = CommandProbe(tmp_path, 'writer-cap')
    try:
        probe.ready(); old = probe.start('old', True); probe.finish(3)
        cap = json.loads((tmp_path / 'writer-cap.json').read_text())
        assert cap['size'] >= 131072 - 16384 and cap['size'] < 131072 + 16 * 1024**2
        journal = SessionJournal(probe.home / 'state' / 'sessions.sqlite3', probe.catalog)
        assert journal.session(old['session_id'])['phase'] != 'completed'
        assert len(journal.status()['units']) == 1
        token = journal.session(old['session_id'])['task']['token']
        assert journal.scratch(token)['state'] == 'candidate_ready'
        assert journal.settlement(token) is None and journal.validation(token) is None
        assert not (probe.home / 'media' / 'old.mp4').exists()
        assert hashlib.sha256((tmp_path / 'one.flv').read_bytes()).hexdigest() == original
    finally:
        stop_probe(probe)


@pytest.mark.parametrize('failure', ['unavailable-tool', 'wrong-source', 'existing-home', 'wrong-catalog'])
def test_actual_command_identity_refusals_do_not_recreate_state(tmp_path, failure):
    generate(tmp_path)
    home = tmp_path / 'pilot-home'
    catalog = None
    original = None
    if failure in {'existing-home', 'wrong-catalog'}:
        first = CommandProbe(tmp_path)
        first.ready(); first.control('shutdown'); first.finish()
        catalog = first.catalog
        original = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in home.rglob('*') if p.is_file()}
    probe = CommandProbe(tmp_path, home=home, catalog=(str(__import__('uuid').uuid4())
        if failure == 'wrong-catalog' else catalog), reopen=failure == 'wrong-catalog',
        ffmpeg=tmp_path / 'missing.exe' if failure == 'unavailable-tool' else None,
        source_hash='0' * 64 if failure == 'wrong-source' else None)
    try:
        probe.finish(2)
        assert not any(e['event'] == 'ready' for e in probe.events())
        if original is not None:
            assert all(hashlib.sha256(p.read_bytes()).hexdigest() == sha for p, sha in original.items())
        else:
            assert not home.exists()
    finally:
        stop_probe(probe)


def test_actual_command_failed_native_startup_retains_primary_and_explicit_retry(tmp_path):
    generate(tmp_path); probe = CommandProbe(tmp_path, 'startup-native-close')
    try:
        wait(lambda: any(e['event'] == 'shutdown' and not e['complete'] for e in probe.events()))
        assert probe.process.poll() is None
        assert not any(e['event'] == 'ready' for e in probe.events())
        assert next(e for e in probe.events() if e['event'] == 'failure')['primary_type'] == 'ValueError'
        marker = (probe.home / 'pilot.json').read_bytes()
        probe.control('cleanup')
        wait(lambda: len([e for e in probe.events() if e['event'] == 'shutdown']) >= 2)
        assert not [e for e in probe.events() if e['event'] == 'shutdown'][-1]['complete']
        (tmp_path / 'repair').write_text('remove only protected exact native test handle')
        probe.control('cleanup'); events = probe.finish(2)
        assert events[-1]['primary_type'] == 'ValueError' and events[-1]['complete']
        assert (probe.home / 'pilot.json').read_bytes() == marker
    finally:
        stop_probe(probe)
