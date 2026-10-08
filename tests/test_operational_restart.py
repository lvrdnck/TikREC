"""Connected queued/prepared/unsupported reopen, explicit refusal and known identity."""
import hashlib
import json
import os
import socket

import pytest

from tests.operational_helpers import Probe
from tests.pilot_test_helpers import generate, wait
from tikrec.session_journal import SessionJournal

pytestmark = pytest.mark.skipif(os.name != 'nt', reason='native Windows service')


@pytest.mark.parametrize('mode', ['prepared', 'unsupported'])
def test_restart_supported_prepared_and_unsupported_pinned_state(tmp_path, mode):
    generate(tmp_path)
    first = Probe(tmp_path, mode).launch(init=True).launch()
    try:
        first.ready(); value = first.start('old', True); sid = value['session_id']
        wait(lambda: first.client.health()['finalization']['paused_reason'] is not None)
        first.control(); first.finish(3)
        journal = SessionJournal(first.home / 'state' / 'sessions.sqlite3', first.catalog)
        before = journal.session(sid)
        originals = {p: hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in (first.home / 'media').rglob('*') if p.is_file()}
        second = Probe(tmp_path, home=first.home, catalog=first.catalog).launch()
        try:
            second.ready()
            if mode == 'prepared':
                wait(lambda: second.client.status(sid)['output_completed'])
                assert not journal.status()['units']
            else:
                wait(lambda: second.client.status(sid)['needs_attention'])
                assert journal.session(sid) == before
                assert len(journal.status()['units']) == 1
                assert not second.client.status(sid)['output_completed']
            second.control(); second.finish(0 if mode == 'prepared' else 3)
            assert all(hashlib.sha256(p.read_bytes()).hexdigest() == h for p, h in originals.items())
        finally:
            second.stop()
    finally:
        first.stop()


def test_unclaimed_pressure_queue_restarts_and_returns_units(tmp_path):
    generate(tmp_path)
    first = Probe(tmp_path).launch(init=True).launch()
    try:
        first.ready(); value = first.start('writer', True); sid = value['session_id']
        wait(lambda: (tmp_path / 'source-held').exists())
        (tmp_path / 'free.txt').write_text(str(2 * 1024**3))
        first.client.stop(sid)
        wait(lambda: first.client.status(sid)['finalization_state'] == 'queued')
        first.control(); first.finish()
        journal = SessionJournal(first.home / 'state' / 'sessions.sqlite3', first.catalog)
        assert len(journal.status()['units']) == 1
        assert journal.session(sid)['task']['token'] is None
        (tmp_path / 'free.txt').write_text(str(30 * 1024**3))
        second = Probe(tmp_path, home=first.home, catalog=first.catalog).launch()
        try:
            second.ready()
            wait(lambda: second.client.status(sid)['output_completed'])
            assert not journal.status()['units']
            second.control(); second.finish()
        finally:
            second.stop()
    finally:
        first.stop()


@pytest.mark.parametrize('missing', ['config', 'token', 'tool', 'state'])
def test_headless_refusal_does_not_create_state(tmp_path, missing):
    probe = Probe(tmp_path)
    if missing == 'config':
        probe.config.unlink()
    elif missing == 'token':
        probe.token.unlink()
    elif missing == 'tool':
        probe.args[probe.args.index('--ffprobe') + 1] = str(tmp_path / 'missing.exe')
    probe.launch()
    probe.finish(2)
    assert not probe.home.exists()
    assert not any(e.get('event') == 'ready' for e in probe.events())


def test_single_authority_refuses_competing_command_without_rewriting_log(tmp_path):
    generate(tmp_path)
    first = Probe(tmp_path).launch(init=True).launch()
    try:
        first.ready()
        separate = tmp_path / 'second'; separate.mkdir()
        second = Probe(separate, home=first.home, catalog=first.catalog, config=first.config).launch()
        second.finish(2)
        assert not any(e.get('event') == 'ready' for e in second.events())
        assert first.client.health()['available_slots'] == 2
        first.control(); first.finish()
    finally:
        first.stop()


def test_listener_refusal_precedes_worker_or_automatic_capture(tmp_path):
    probe = Probe(tmp_path)
    probe.write_config(('fixture.auto',))
    probe.launch(init=True)
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0)); listener.listen()
        probe.launch(extra=('--port', str(listener.getsockname()[1])))
        probe.finish(2)
    journal = SessionJournal(probe.home / 'state' / 'sessions.sqlite3', probe.catalog)
    assert not journal.history()
    assert not (tmp_path / 'work-started').exists()
