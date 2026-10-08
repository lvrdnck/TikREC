"""Rehearse the real foreground module and native accept loop with generated sources."""
import hashlib
import json
import os
import time
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(os.name != 'nt', reason='native Windows pilot command')
from tests.pilot_test_helpers import CommandProbe, generate, wait, validate
from tikrec.remote import RemoteError
from tikrec.session_journal import SessionJournal


def stop_probe(probe):
    """Repair only disposable fixture barriers, then request product-owned shutdown."""
    (probe.base / 'release').write_text('release fixture barrier')
    (probe.base / 'repair').write_text('repair injected refusal')
    (probe.base / 'confirm-continue').write_text('release fixture confirmation')
    for name in ('writer-a', 'writer-b'):
        (probe.base / (name + '-continue')).write_text('release fixture source')
    if probe.process.poll() is None and probe.home.exists():
        probe.control('shutdown')
        wait(lambda: probe.process.poll() is not None)
    if not probe.stream.closed:
        probe.stream.close()


@pytest.mark.parametrize('mode', ['copy', 'libx264'])
def test_actual_command_overlap_uuid_fifo_outputs_and_originals(tmp_path, mode):
    generate(tmp_path)
    originals = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in tmp_path.glob('*.flv')}
    probe = CommandProbe(tmp_path, mode)
    try:
        ready = probe.ready()
        assert probe.client.monitoring()['creators'] == []
        old = probe.start('old', True)
        wait(lambda: (tmp_path / 'held').exists())
        plan = json.loads((tmp_path / 'old-plan.json').read_text())
        assert plan['copy'] == (mode == 'copy')
        assert plan['h'] is not None
        old_status = probe.client.status(old['session_id'])
        assert not old_status['active'] and not old_status['output_completed']
        a = probe.start('writer-a', True); b = probe.start('writer-b')
        wait(lambda: all((tmp_path / (name + '-half')).exists() for name in ('writer-a', 'writer-b')))
        counts = [probe.client.status(item['session_id'])['bytes_written'] for item in (a, b)]
        assert all(value > 0 for value in counts)
        assert a['origin_slot_id'] == old['origin_slot_id']
        assert probe.client.stop(old['session_id'])['stop_result'] == 'capture_already_closed'
        assert all(probe.client.status(item['session_id'])['active'] for item in (a, b))
        with pytest.raises(RemoteError, match='409'):
            probe.client.stop()
        for name in ('writer-a', 'writer-b'):
            (tmp_path / (name + '-continue')).write_text('continue second half')
        wait(lambda: all(probe.client.status(item['session_id'])['bytes_written'] > count
                         for item, count in zip((a, b), counts)))
        assert (tmp_path / 'held').exists() and not (tmp_path / 'release').exists()
        probe.client.stop(b['session_id'])
        (tmp_path / 'release').write_text('permit original FIFO completion')
        wait(lambda: all(probe.client.status(item['session_id'])['output_completed'] for item in (old, a, b)))
        assert probe.client.status(old['session_id'])['session_id'] == old['session_id']
        journal = SessionJournal(Path(ready['catalog']), probe.catalog)
        h = journal.session(old['session_id'])['seal']
        order = [json.loads(line)['name'] for line in (tmp_path / 'completion-order.jsonl').read_text().splitlines()]
        assert order[0] == 'old' and set(order) == {'old', 'writer-a', 'writer-b'}
        assert journal.operation(plan['h_operation']) == plan['h']
        assert h == plan['seal']
        assert not journal.status()['units']
        probe.control('shutdown'); probe.finish()
        for path, expected in plan['hashes'].items():
            actual = Path(path)
            if actual.name == 'session.json':
                actual = actual.parent / ('.tikrec-manifest-' + plan['token'] + '.original.json')
            assert hashlib.sha256(actual.read_bytes()).hexdigest() == expected
        assert SessionJournal(Path(ready['catalog']), probe.catalog).session(old['session_id'])['seal'] == h
        assert all(hashlib.sha256(p.read_bytes()).hexdigest() == sha for p, sha in originals.items())
        assert b''.join(p.read_bytes() for p in sorted((probe.home / 'media' / 'old.parts').glob('*.raw'))) == (
            (tmp_path / 'one.flv').read_bytes() + (tmp_path / ('two.flv' if mode == 'libx264' else 'one.flv')).read_bytes())
        assert not list((probe.home / 'media' / 'writer-b.parts').glob('*.raw'))
        for name in ('old', 'writer-a', 'writer-b'):
            validate(probe.home / 'media' / (name + '.parts'), tmp_path)
    finally:
        stop_probe(probe)


def test_actual_command_low_space_admission_and_original_inflight_stop(tmp_path):
    generate(tmp_path); probe = CommandProbe(tmp_path)
    try:
        probe.ready(); a = probe.start('writer-a', True)
        wait(lambda: (tmp_path / 'writer-a-half').exists())
        (tmp_path / 'free.txt').write_text(str(12 * 1024**3))
        with pytest.raises(RemoteError, match='409'):
            probe.start('refused')
        assert len(SessionJournal(probe.home / 'state' / 'sessions.sqlite3', probe.catalog).history()) == 1
        (tmp_path / 'free.txt').write_text(str(7 * 1024**3))
        shutdown = probe.finish(3)
        assert shutdown[-1]['captures_joined'] and shutdown[-1]['authority_released']
        row = SessionJournal(probe.home / 'state' / 'sessions.sqlite3', probe.catalog).session(a['session_id'])
        assert row['stop'] and row['seal'] is not None
        assert any(e.get('reason') == 'pilot_low_space_stop' for e in probe.events())
    finally:
        stop_probe(probe)


def test_actual_command_incomplete_shutdown_retains_original_sqlite_until_cleanup(tmp_path):
    generate(tmp_path); probe = CommandProbe(tmp_path, 'sqlite-close')
    try:
        probe.ready()
        assert probe.client.health()['active_count'] is None
        wait(lambda: (tmp_path / 'sqlite-close-threads.jsonl').exists())
        probe.control('shutdown')
        wait(lambda: any(e['event'] == 'shutdown' and not e['complete'] for e in probe.events()))
        assert probe.process.poll() is None
        probe.control('cleanup')
        wait(lambda: len([e for e in probe.events() if e['event'] == 'shutdown']) >= 2)
        assert not [e for e in probe.events() if e['event'] == 'shutdown'][-1]['complete']
        (tmp_path / 'repair').write_text('remove injected original close fault')
        probe.control('cleanup'); probe.finish()
        rows = [json.loads(line) for line in (tmp_path / 'sqlite-close-threads.jsonl').read_text().splitlines()]
        assert all(row['creator'] == row['closer'] for row in rows) and rows[-1]['repaired']
    finally:
        stop_probe(probe)


@pytest.mark.parametrize('mode', ['prepared', 'unsupported'])
def test_actual_command_restart_scope_preserves_originals_and_accounting(tmp_path, mode):
    generate(tmp_path); first = CommandProbe(tmp_path, mode)
    try:
        first.ready(); old = first.start('old', True)
        first.finish(3)
        journal = SessionJournal(first.home / 'state' / 'sessions.sqlite3', first.catalog)
        before = journal.session(old['session_id'])
        media = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in (first.home / 'media').rglob('*')
                 if p.is_file() and p.name != '.tikrec-lifecycle.lock'}
        second = CommandProbe(tmp_path, 'reopen', home=first.home, catalog=first.catalog, reopen=True)
        try:
            if mode == 'prepared':
                second.ready()
                wait(lambda: second.client.status(old['session_id'])['output_completed'])
                assert not journal.status()['units']
                second.control('shutdown'); second.finish()
                validate(first.home / 'media' / 'old.parts', tmp_path)
            else:
                second.finish(3)
                assert journal.session(old['session_id']) == before
                assert len(journal.status()['units']) == 1
                assert not (first.home / 'media' / 'old.mp4').exists()
            assert all(hashlib.sha256(p.read_bytes()).hexdigest() == sha for p, sha in media.items())
        finally:
            stop_probe(second)
    finally:
        stop_probe(first)
