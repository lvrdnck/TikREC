"""Actual headless operational command retires written failures with attention exit 3."""

import hashlib
import json
import os
import subprocess
import sys

import pytest

from tests.operational_helpers import Probe
from tests.pilot_test_helpers import ROOT, generate, wait
from tikrec.session_journal import SessionJournal

pytestmark = pytest.mark.skipif(os.name != 'nt', reason='native Windows operational CLI')


class WrittenProbe(Probe):
    """Use ordinary CLI argv with only generated source and prospective witness seams."""

    def launch_written(self):
        """Record launch before creating the supervised generated command."""
        command = [sys.executable, '-m', 'tests.operational_written_probe', *self.args]
        (self.base / 'written-launch.json').write_text(json.dumps({'argv': command, 'cwd': str(ROOT)}))
        self.log = self.base / 'written.log'
        self.stream = self.log.open('wb')
        self.process = subprocess.Popen(command, cwd=ROOT, env=self.env, stdin=subprocess.DEVNULL,
                                        stdout=self.stream, stderr=subprocess.STDOUT)
        return self

    def witnesses(self):
        """Read only complete recorded witnesses from this newly generated home."""
        path = self.base / 'written-witness.jsonl'
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def stop(self):
        """Remove only a generated handle fault before the original-owner cleanup nonce."""
        (self.base / 'repair-written').touch()
        if self.process is not None and self.process.poll() is None and any(
                row['event'] == 'cleanup-return' for row in self.witnesses()):
            # An incomplete owner accepts cleanup, never another shutdown retry.
            self.control('cleanup')
            self.process.wait(60)
        super().stop()


def test_actual_written_failure_attention_exit_and_idle_reopen(tmp_path):
    generate(tmp_path)
    probe = WrittenProbe(tmp_path).launch(init=True).launch_written()
    try:
        probe.ready()
        sid = probe.start('written', True)['session_id']
        wait(lambda: any(r['event'] == 'capture-return' for r in probe.witnesses()))
        before = next(r for r in probe.witnesses() if r['event'] == 'capture-return')
        assert before['session'] == sid and before['writer_openings'] > 0
        assert before['cause_type'] == 'StopIteration'
        probe.control(); probe.finish(3)
        after = [r for r in probe.witnesses() if r['event'] == 'cleanup-return'][-1]
        assert after['result']['complete'] and after['authority_retired']
        assert after['admission_fenced'] and not after['sqlite_owned'] and not after['threads']
        assert after['state_pins'] == after['state_guards'] == 0
        capture = next(c for c in after['captures'] if c['session'] == sid)
        assert capture['bridge'] == before['owner'] and capture['failure'] == before['failure']
        assert capture['done'] and capture['joined'] and capture['lease_closed']
        assert capture['lease_native_retired'] and capture['raw_retired'] and capture['writers_retired']
        assert capture['fence_closed'] and capture['inflight'] == 0
        assert capture['sources_opened'] == capture['sources_closed'] > 0
        parts = probe.home / 'media' / 'written.parts'
        assert all(hashlib.sha256((parts / p).read_bytes()).hexdigest() == h
                   for p, h in before['hashes'].items())
        journal = SessionJournal(probe.home / 'state' / 'sessions.sqlite3', probe.catalog)
        assert journal.session(sid) == before['row'] and journal.status() == before['status']
        assert len(journal.status()['units']) == 1 and not (probe.home / 'media' / 'written.mp4').exists()
        # Reopen this NEW same-code fixture, never an old fingerprint-bound home.
        probe.launch().ready()
        assert probe.client.status(sid)['needs_attention']
        # Durable capture bindings remain occupied even though no local writer is relaunched.
        assert len(probe.client.recordings()['outstanding_sessions']) == 1
        probe.control(); probe.finish(0)
        assert journal.session(sid) == before['row'] and journal.status() == before['status']
        assert all(hashlib.sha256((parts / p).read_bytes()).hexdigest() == h
                   for p, h in before['hashes'].items())
    finally:
        probe.stop()  # Owned nonce only; there is no termination fallback.


def test_actual_written_native_fault_retains_same_supervisor_until_fresh_cleanup(tmp_path):
    import time
    generate(tmp_path)
    probe = WrittenProbe(tmp_path).launch(init=True)
    probe.env['TIKREC_WRITTEN_CLOSE_FAULT'] = 'part'
    probe.launch_written()
    try:
        probe.ready()
        sid = probe.start('written', True)['session_id']
        wait(lambda: any(r['event'] == 'capture-return' for r in probe.witnesses()))
        before = next(r for r in probe.witnesses() if r['event'] == 'capture-return')
        probe.control()
        wait(lambda: any(r['event'] == 'cleanup-return' for r in probe.witnesses()))
        first = [r for r in probe.witnesses() if r['event'] == 'cleanup-return'][-1]
        assert not first['result']['complete'] and probe.process.poll() is None
        assert first['admission_fenced'] and first['captures'][0]['joined']
        assert not first['captures'][0]['lease_closed'] and not first['captures'][0]['writers_retired']
        count = len(probe.witnesses())
        time.sleep(0.3)
        assert len(probe.witnesses()) == count  # No automatic retry while supervision continues.
        (tmp_path / 'repair-written').touch()
        probe.control('cleanup'); probe.finish(3)
        last = [r for r in probe.witnesses() if r['event'] == 'cleanup-return'][-1]
        assert first['owner'] == last['owner'] and last['result']['complete']
        assert last['authority_retired'] and not last['sqlite_owned'] and not last['threads']
        capture = last['captures'][0]
        assert capture['bridge'] == before['owner'] and capture['failure'] == before['failure']
        assert capture['writers_retired'] and capture['lease_native_retired']
        journal = SessionJournal(probe.home / 'state' / 'sessions.sqlite3', probe.catalog)
        assert journal.session(sid) == before['row'] and journal.status() == before['status']
        parts = probe.home / 'media' / 'written.parts'
        assert all(hashlib.sha256((parts / p).read_bytes()).hexdigest() == h
                   for p, h in before['hashes'].items())
    finally:
        probe.stop()
