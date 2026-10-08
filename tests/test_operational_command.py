"""Connected headless normal-CLI verification, generated native Windows media only."""
import json
import os
import hashlib

import pytest

from tests.operational_helpers import Probe
from tests.pilot_test_helpers import generate, wait, validate
from tikrec.remote import RemoteError
from tikrec.session_journal import SessionJournal
from tikrec.configuration import Configuration
from tikrec.retention_plan import plan_retention

pytestmark = pytest.mark.skipif(os.name != 'nt', reason='native Windows journal mode')


def test_explicit_init_manual_ten_successes_addressed_history_and_shutdown(tmp_path):
    generate(tmp_path)
    probe = Probe(tmp_path).launch(init=True).launch()
    try:
        probe.ready()
        sessions = []
        for index in range(10):
            value = probe.start('manual' + str(index), True)
            sid = value['session_id']; sessions.append(sid)
            wait(lambda: probe.client.status(sid)['output_completed'])
        assert probe.client.status(sessions[0])['output_completed']
        assert probe.client.health()['finalization']['outstanding_units'] == 0
        journal = SessionJournal(probe.home / 'state' / 'sessions.sqlite3', probe.catalog)
        assert len(journal.history()) == 10
        assert not journal.status()['units']
        registry = json.loads((tmp_path / 'registry.json').read_text())
        assert registry['guards'] <= 8 and registry['captures'] <= 2 and registry['attempts'] <= 2
        probe.control(); probe.finish()
        validate(probe.home / 'media' / 'manual9.parts', tmp_path)
        files = [p for p in (probe.home / 'media').rglob('*') if p.is_file()]
        original = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
        plan = plan_retention(probe.home / 'media', Configuration(retention_max_age_days=1),
                              clock=lambda: 4_000_000_000)
        assert all(s['classification'] != 'eligible' for s in plan['sessions'])
        assert all(hashlib.sha256(p.read_bytes()).hexdigest() == h for p, h in original.items())
        logs = [json.loads(line) for p in (probe.home / 'logs').glob('events-*.jsonl')
                for line in p.read_text().splitlines()]
        assert any(e['event'] == 'startup' and e['source']['python_version'] for e in logs)
        assert any(e['event'] == 'exit' and e['complete'] and e['exit_code'] == 0 for e in logs)
    finally:
        probe.stop()


def test_configuration_change_uses_actual_libx264_pipeline(tmp_path):
    generate(tmp_path)
    probe = Probe(tmp_path, 'changed').launch(init=True).launch()
    try:
        probe.ready(); sid = probe.start('changed', True)['session_id']
        wait(lambda: probe.client.status(sid)['output_completed'])
        journal = SessionJournal(probe.home / 'state' / 'sessions.sqlite3', probe.catalog)
        token = journal.session(sid)['task']['token']
        assembly = journal.child_history(token)
        assert assembly
        # Recipe evidence comes from the real owned writer, not a mocked completion.
        assert 'libx264' in json.dumps(assembly)
        probe.control(); probe.finish()
        validate(probe.home / 'media' / 'changed.parts', tmp_path)
    finally:
        probe.stop()


def test_failed_diagnostic_sink_never_resends_accepted_start(tmp_path):
    generate(tmp_path)
    probe = Probe(tmp_path, 'sink').launch(init=True).launch()
    try:
        probe.ready(); sid = probe.start('once', True)['session_id']
        probe.finish(2)
        journal = SessionJournal(probe.home / 'state' / 'sessions.sqlite3', probe.catalog)
        assert [s['id'] for s in journal.history()] == [sid]
        assert journal.session(sid)['phase'] in {'completed', 'queued'}
    finally:
        probe.stop()


def test_automatic_reload_and_startup_raw_policy(tmp_path):
    generate(tmp_path)
    probe = Probe(tmp_path)
    probe.write_config(('fixture.auto',), ('fixture.auto',))
    probe.launch(init=True).launch()
    try:
        probe.ready()
        journal = SessionJournal(probe.home / 'state' / 'sessions.sqlite3', probe.catalog)
        wait(lambda: len(journal.history()) == 1)
        first = journal.history()[0]['id']
        wait(lambda: probe.client.status(first)['output_completed'])
        assert probe.client.status(first)['raw_copy_enabled']
        probe.write_config(('fixture.second',), ('fixture.second',))
        wait(lambda: len(journal.history()) == 2)
        second = journal.history()[1]['id']
        wait(lambda: probe.client.status(second)['output_completed'])
        assert not probe.client.status(second)['raw_copy_enabled']
        probe.control(); probe.finish()
    finally:
        probe.stop()


def test_capture_while_finalizer_waits_original_uuid_stop_and_queued_restart(tmp_path):
    generate(tmp_path)
    probe = Probe(tmp_path, 'hold').launch(init=True).launch()
    try:
        probe.ready(); old = probe.start('old', True)
        wait(lambda: (tmp_path / 'finalizer-held').exists())
        new = probe.start('writer', True)
        wait(lambda: (tmp_path / 'source-held').exists())
        assert probe.client.status(new['session_id'])['active']
        assert probe.client.stop(old['session_id'])['stop_result'] == 'capture_already_closed'
        probe.client.stop(new['session_id'])
        (tmp_path / 'release-finalizer').touch()
        wait(lambda: probe.client.status(old['session_id'])['output_completed'])
        wait(lambda: probe.client.status(new['session_id'])['output_completed'])
        probe.control(); probe.finish()
    finally:
        probe.stop()


def test_low_unknown_pressure_defers_queue_stops_original_capture_and_restores(tmp_path):
    generate(tmp_path)
    probe = Probe(tmp_path).launch(init=True).launch()
    try:
        probe.ready(); value = probe.start('writer', True); sid = value['session_id']
        wait(lambda: (tmp_path / 'source-held').exists())
        (tmp_path / 'free.txt').write_text(str(4 * 1024**3))
        with pytest.raises(RemoteError, match='409'):
            probe.start('refused')
        (tmp_path / 'free.txt').write_text('unknown')
        wait(lambda: not probe.client.status(sid)['active'])
        assert not probe.client.status(sid)['output_completed']
        assert probe.client.status(sid)['stop_requested']
        (tmp_path / 'free.txt').write_text(str(30 * 1024**3))
        wait(lambda: probe.client.status(sid)['output_completed'])
        assert probe.client.status(sid)['interrupted']
        probe.control(); probe.finish()
    finally:
        probe.stop()


@pytest.mark.parametrize('free', ['unknown', str(4 * 1024**3)])
def test_pressure_before_manual_admission_creates_no_intent(tmp_path, free):
    probe = Probe(tmp_path).launch(init=True).launch()
    try:
        probe.ready(); (tmp_path / 'free.txt').write_text(free)
        with pytest.raises(RemoteError, match='409'):
            probe.start('refused')
        journal = SessionJournal(probe.home / 'state' / 'sessions.sqlite3', probe.catalog)
        assert not journal.history() and not journal.status()['units']
        probe.control(); probe.finish()
    finally:
        probe.stop()
