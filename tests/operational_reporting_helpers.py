"""Headless CLI reporting probes with prospective launch and independent witnesses."""
import json
import os
import subprocess
import sys
import time
from threading import Thread

from tests.operational_helpers import Probe
from tests.pilot_test_helpers import ROOT, SECRET, wait
from tikrec.remote import RemoteClient


class ReportingProbe(Probe):
    """Run unmodified product CLI behind only generated fault/observation seams."""

    def launch_fault(self, stage='ready', fault='pipe', owner='', supervision=False):
        """Record actual argv/environment before creating the native child."""
        self.env.update(TIKREC_REPORT_STAGE=stage, TIKREC_REPORT_FAULT=fault,
                        TIKREC_REPORT_OWNER=owner)
        (self.base / 'native-held.bin').write_bytes(b'generated exact native owner')
        if supervision:
            (self.base / 'supervision').touch()
        command = [sys.executable, '-m', 'tests.operational_reporting_probe', *self.args]
        (self.base / 'report-launch.json').write_text(json.dumps({
            'argv': command, 'cwd': str(ROOT), 'entrypoint': 'tikrec.cli',
            'fault': fault, 'stage': stage, 'retained_owner': owner}))
        self.log = self.base / 'report.log'
        self.stream = self.log.open('wb')
        self.process = subprocess.Popen(command, cwd=ROOT, env=self.env, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE if fault == 'pipe' else self.stream,
            stderr=subprocess.PIPE if fault == 'pipe' else subprocess.STDOUT)
        (self.base / 'report-pid.json').write_text(json.dumps({'pid': self.process.pid}))
        if fault == 'pipe':
            def close_pipe():
                # Close actual subprocess readers at the selected product receipt,
                # not a substitute writer that merely raises BrokenPipeError.
                while self.process.poll() is None:
                    if (self.base / 'close-pipe').exists():
                        self.process.stdout.close(); self.process.stderr.close()
                        (self.base / 'pipe-closed').write_text(json.dumps({'pid': self.process.pid,
                            'stdout_reader_closed': True, 'stderr_reader_closed': True}))
                        return
                    time.sleep(0.01)
            Thread(target=close_pipe, daemon=True).start()
        return self

    def witnesses(self):
        """Read complete prospective observations, never reconstruct failed product output."""
        path = self.base / 'witness.jsonl'
        if not path.exists():
            return []
        rows = []
        for line in path.read_text().splitlines():
            try:
                rows.append(json.loads(line))
            except ValueError:
                pass
        return rows

    def connect(self):
        """Use an independently observed actual listener for fault-at-ready cases."""
        wait(lambda: any(r['event'] == 'composed' for r in self.witnesses()))
        port = next(r['port'] for r in self.witnesses() if r['event'] == 'composed')
        self.client = RemoteClient('http://127.0.0.1:' + str(port), token=SECRET)

    def stopped(self):
        """Wait for product cleanup or a separately witnessed baseline escape."""
        wait(lambda: any(r['event'] in {'cleanup-return', 'escaped'} for r in self.witnesses()), 45)
        rows = self.witnesses()
        assert not any(r['event'] == 'escaped' for r in rows), rows
        return [r for r in rows if r['event'] == 'cleanup-return'][-1]

    def stop(self):
        """Repair generated faults, request explicit product cleanup; label baseline rescue."""
        for name in ('repair', 'release-source', 'release-finalizer', 'rescue'):
            (self.base / name).touch()
        if self.process and self.process.poll() is None:
            self.control('cleanup')
            self.process.wait(60)
        if hasattr(self, 'stream'):
            self.stream.close()
