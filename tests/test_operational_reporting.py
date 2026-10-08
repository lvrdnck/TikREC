"""Reporting failure must initiate real owned cleanup, never replace its result."""
import hashlib
import json
import os
import time

import pytest

from tests.operational_reporting_helpers import ReportingProbe
from tests.pilot_test_helpers import generate, wait, validate
from tikrec.session_journal import SessionJournal

pytestmark = pytest.mark.skipif(os.name != 'nt', reason='native Windows CLI shutdown')


def retired(probe, code):
    """Require original-owner native/SQLite/thread retirement before actual exit."""
    probe.finish(code)
    rows = probe.witnesses()
    row = next(r for r in rows if r['event'] == 'product-exit')
    assert (row['result'] is None or row['result']['complete']) and row['pins'] == row['guards'] == 0
    assert not row['native_retained'] and not row['reader_retained']
    if row['authority_retired'] is not None:
        assert row['authority_retired'] and not row['sqlite_owned']
        assert row['closed'] and row['stopping']
        assert row['admission_fenced']
    assert not row['threads'], row
    assert {r['owner'] for r in rows if 'owner' in r} == {row['owner']}
    assert not any(r['event'] == 'baseline-intervention' for r in rows)


@pytest.mark.parametrize('stage', ['startup', 'ready', 'shutdown', 'exit', 'initialized'])
@pytest.mark.parametrize('fault', ['pipe', 'write', 'flush', 'healthy'])
def test_lifecycle_output_failure_retires_original_empty_owner(tmp_path, stage, fault):
    probe = ReportingProbe(tmp_path)
    if stage != 'initialized':
        probe.launch(init=True)
    else:
        probe.args.append('--journal-init')
    probe.launch_fault(stage, fault)
    try:
        if stage in {'shutdown', 'exit'} or fault == 'healthy' and stage != 'initialized':
            probe.connect(); probe.control()
        probe.stopped() if stage not in {'exit', 'initialized'} else None
        retired(probe, 0 if fault == 'healthy' else 2)
        if stage == 'exit':
            disk = [json.loads(line) for p in (probe.home / 'logs').glob('events-*.jsonl')
                    for line in p.read_text().splitlines()]
            assert [r for r in disk if r['event'] == 'exit'][-1]['exit_code'] == (0 if fault == 'healthy' else 2)
    finally:
        probe.stop()


@pytest.mark.parametrize('retained', ['', 'native', 'sqlite'])
def test_primary_and_attached_originals_survive_combined_reporting_failure(tmp_path, retained):
    probe = ReportingProbe(tmp_path).launch(init=True)
    probe.launch_fault('failure', 'pipe', retained)
    try:
        first = probe.stopped()
        assert first['primary_same'] and first['primary_type'] == 'ValueError'
        if retained:
            assert not first['result']['complete'] and probe.process.poll() is None
            assert first['native_retained'] if retained == 'native' else first['reader_retained']
            marker = (probe.home / 'service.json').read_bytes()
            count = len([r for r in probe.witnesses() if r['event'] == 'cleanup-enter'])
            time.sleep(0.3)
            assert len([r for r in probe.witnesses() if r['event'] == 'cleanup-enter']) == count
            probe.control('shutdown')  # After stopping, only fresh cleanup is supported.
            time.sleep(0.3)
            assert len([r for r in probe.witnesses() if r['event'] == 'cleanup-enter']) == count
            (tmp_path / 'disk-failed').touch()
            (tmp_path / 'repair').touch()
            probe.control('cleanup')
            retired(probe, 2)
            assert (probe.home / 'service.json').read_bytes() == marker
        else:
            retired(probe, 2)
        last = next(r for r in probe.witnesses() if r['event'] == 'product-exit')
        assert last['primary_same']
        assert len(last['reporting']) <= 2
    finally:
        probe.stop()


@pytest.mark.parametrize('retained', ['native', 'sqlite'])
def test_inherited_cleanup_emission_cannot_bypass_explicit_retry(tmp_path, retained):
    probe = ReportingProbe(tmp_path).launch(init=True).launch_fault('shutdown', 'flush', retained,
                                                                  supervision=True)
    try:
        probe.connect()
        (tmp_path / 'trigger').touch()
        first = probe.stopped()
        assert first['primary_same'] and not first['result']['complete']
        assert probe.process.poll() is None and first['closed'] and first['stopping']
        before = probe.witnesses()
        time.sleep(0.3)
        assert len(probe.witnesses()) == len(before)
        (tmp_path / 'repair').touch()
        probe.control('cleanup'); retired(probe, 2)
        assert next(r for r in probe.witnesses() if r['event'] == 'product-exit')['primary_same']
    finally:
        probe.stop()


@pytest.mark.parametrize('combined', [False, True])
def test_reporting_failure_during_generated_capture_and_finalization(tmp_path, combined):
    generate(tmp_path)
    originals = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in tmp_path.glob('*.flv')}
    probe = ReportingProbe(tmp_path, 'hold').launch(init=True).launch_fault('failure', 'pipe', supervision=True)
    try:
        probe.connect(); old = probe.start('old', True)['session_id']
        wait(lambda: (tmp_path / 'finalizer-held').exists())
        active = probe.start('writer', True)['session_id']
        wait(lambda: (tmp_path / 'source-held').exists())
        journal = SessionJournal(probe.home / 'state' / 'sessions.sqlite3', probe.catalog)
        seal = journal.session(old)['seal']
        if combined:
            (tmp_path / 'disk-failed').touch()
        else:
            (tmp_path / 'trigger').touch()
        wait(lambda: any(r['event'] == 'cleanup-enter' for r in probe.witnesses()))
        wait(lambda: journal.session(active)['stop'])
        # Product shutdown fences listener, monitor and admission before finalizer grace.
        assert len(journal.history()) == 2
        (tmp_path / 'release-finalizer').touch()
        probe.stopped(); retired(probe, 2)
        assert journal.session(old)['seal'] == seal
        assert {s['id'] for s in journal.history()} == {old, active}
        assert journal.session(active)['stop']
        assert journal.session(old)['phase'] == 'completed'
        assert journal.session(active)['phase'] == 'queued' and len(journal.status()['units']) == 1
        validate(probe.home / 'media' / 'old.parts', tmp_path)
        assert all(hashlib.sha256((tmp_path / n).read_bytes()).hexdigest() == h for n, h in originals.items())
        last = next(r for r in probe.witnesses() if r['event'] == 'product-exit')
        assert len(last['reporting']) == (2 if combined else 1)
        assert len([r for r in probe.witnesses() if r['event'] == 'console-write']) <= 2
        if combined:
            assert len([r for r in probe.witnesses() if r['event'] == 'disk-write']) == 1
    finally:
        probe.stop()


def test_failure_before_owner_with_unavailable_stdout_stderr(tmp_path):
    probe = ReportingProbe(tmp_path)
    probe.args[probe.args.index('--token-file') + 1] = str(tmp_path / 'missing-token')
    probe.launch_fault('failure', 'pipe')
    try:
        probe.finish(2)
        assert not probe.home.exists()
        assert not any(r['event'] == 'owner-created' for r in probe.witnesses())
        assert (tmp_path / 'pipe-closed').exists()
    finally:
        probe.stop()
