"""Prospective subprocess/argv/tool/exit evidence for generated headless service tests."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

from tests.pilot_test_helpers import SECRET, ROOT, wait
from tikrec.remote import RemoteClient


class Probe:
    """Create disposable explicit config and launch through actual normal CLI parsing."""

    def __init__(self, base, mode='normal', *, home=None, catalog=None, config=None):
        self.base, self.home = base, home or base / 'service-home'
        self.catalog = catalog or str(uuid4())
        self.config = config or base / 'config.json'
        self.token = base / 'token.txt'
        self.token.write_text(SECRET)
        if not self.config.exists():
            self.write_config(())
        self.env = dict(os.environ, TIKREC_OPERATIONAL_TEST_ROOT=str(base), TIKREC_OPERATIONAL_TEST_MODE=mode)
        self.env.pop('TIKREC_TOKEN', None)
        self.args = ['--config', str(self.config), 'serve', '--journal-home', str(self.home),
            '--journal-catalog-id', self.catalog, '--token-file', str(self.token), '--port', '0',
            '--ffmpeg', shutil.which('ffmpeg'), '--ffprobe', shutil.which('ffprobe')]
        self.process = None

    def write_config(self, creators, raw=()):
        """Atomically replace generated creator configuration without product-policy mutation."""
        value = {'schema_version': 1, 'output_directory': str(self.home / 'media'),
                 'minimum_free_space_gib': 1, 'monitored_creators': list(creators),
                 'automatic_raw_copy_creators': list(raw)}
        temporary = self.config.with_suffix('.new')
        temporary.write_text(json.dumps(value))
        os.replace(temporary, self.config)

    def launch(self, init=False, extra=()):
        """Save exact launch parameters before process creation; secrets stay in a file."""
        command = [sys.executable, '-m', 'tests.operational_probe', *self.args,
                   *(['--journal-init'] if init else []), *extra]
        name = 'init' if init else 'serve'
        index = 0
        while (self.base / (name + '-launch.json')).exists():
            index += 1
            name = ('init' if init else 'serve') + '-' + str(index)
        (self.base / (name + '-launch.json')).write_text(json.dumps({
            'argv': command, 'cwd': str(ROOT), 'entrypoint': 'tikrec.cli', 'python': sys.executable}))
        self.log = self.base / (name + '.log')
        self.stream = self.log.open('wb')
        self.process = subprocess.Popen(command, cwd=ROOT, env=self.env, stdin=subprocess.DEVNULL,
                                        stdout=self.stream, stderr=subprocess.STDOUT)
        (self.base / (name + '-native-launch.json')).write_text(json.dumps({
            'pid': self.process.pid, 'argv': command, 'cwd': str(ROOT)}))
        if init:
            assert self.process.wait(30) == 0, self.log.read_text(errors='replace')
            self.stream.close()
            (self.base / (name + '-exit.json')).write_text(json.dumps({'returncode': self.process.returncode}))
        return self

    def events(self):
        """Read existing complete foreground receipts, never reconstruct missing events."""
        values = []
        for line in self.log.read_text(errors='replace').splitlines():
            try:
                values.append(json.loads(line))
            except ValueError:
                pass
        return values

    def ready(self):
        """Require actual listener/startup success and authenticated health."""
        def condition():
            assert self.process.poll() is None, self.log.read_text(errors='replace')
            return any(e.get('event') == 'ready' for e in self.events())
        wait(condition)
        event = next(e for e in self.events() if e.get('event') == 'ready')
        self.client = RemoteClient('http://127.0.0.1:' + str(event['port']), token=SECRET)
        return event

    def start(self, name, raw=False):
        """Use real authenticated manual admission and original UUID response."""
        return self.client.start('https://www.tiktok.com/@fixture.' + name + '/live',
                                 str(self.home / 'media' / (name + '.mp4')), raw_copy=raw)

    def control(self, command='shutdown'):
        """Request owned shutdown on the original supervisor without terminating its PID."""
        temporary = self.home / 'control.new'
        temporary.write_text(json.dumps({'operation': str(uuid4()), 'command': command}))
        os.replace(temporary, self.home / 'control.json')

    def finish(self, code=0):
        """Capture actual native command exit and final owned cleanup receipts."""
        assert self.process.wait(60) == code, self.log.read_text(errors='replace')
        self.stream.close()
        assert SECRET not in self.log.read_text(errors='replace')
        (self.base / (self.log.stem + '-exit.json')).write_text(json.dumps({
            'returncode': self.process.returncode, 'events': self.events()}))

    def stop(self):
        """Release generated barriers, then stop only through the product control."""
        (self.base / 'release-source').touch(); (self.base / 'release-finalizer').touch()
        if self.process is not None and self.process.poll() is None:
            self.control()
            self.process.wait(60)
        if hasattr(self, 'stream'):
            self.stream.close()
