"""Disposable subprocess command rehearsal using real Windows loopback sockets."""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from uuid import uuid4

from tikrec.remote import RemoteClient

ROOT = Path(__file__).absolute().parents[1]
SECRET = 'generated-pilot-fixture-0123456789'


def wait(predicate, seconds=90):
    """Wait for actual evidence; elapsed time is never a success criterion."""
    end = time.monotonic() + seconds
    while not predicate():
        assert time.monotonic() < end, 'command rehearsal evidence missing'
        time.sleep(0.02)


def generate(base):
    """Generate both matching and changed AVC/AAC streams without user media."""
    base.mkdir(exist_ok=True)
    for name, size in [('one', '64x64'), ('two', '80x64')]:
        subprocess.run([shutil.which('ffmpeg'), '-v', 'error', '-f', 'lavfi', '-i',
            'testsrc=size=' + size + ':rate=10', '-f', 'lavfi', '-i',
            'sine=frequency=440:sample_rate=44100', '-t', '1.2', '-c:v', 'libx264',
            '-pix_fmt', 'yuv420p', '-g', '3', '-c:a', 'aac', '-f', 'flv',
            str(base / (name + '.flv'))], check=True, capture_output=True, timeout=30)


class CommandProbe:
    """Run the actual module with private offline seams and preserve exact command/logs."""

    def __init__(self, base, mode='copy', *, home=None, catalog=None, reopen=False, port=0, ffmpeg=None, source_hash=None):
        self.base, self.home = base, home or base / 'pilot-home'
        self.catalog = catalog or str(uuid4())
        self.log = base / ('reopen.log' if reopen else 'command.log')
        self.stream = self.log.open('wb')
        self.args = ['--checkout', str(ROOT), '--revision', subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(), '--home', str(self.home),
            '--catalog-id', self.catalog, '--mode', 'reopen' if reopen else 'init',
            '--source-sha256', source_hash or self.source_hash(),
            '--ffmpeg', str(ffmpeg or shutil.which('ffmpeg')), '--ffprobe', shutil.which('ffprobe'), '--port', str(port)]
        environment = dict(os.environ, TIKREC_PILOT_TEST_FIXTURES=str(base), TIKREC_PILOT_TEST_MODE=mode)
        environment.pop('TIKREC_TOKEN', None)
        command = [sys.executable, '-m', 'tests.pilot_command_probe', *self.args]
        (base / ('reopen-command.json' if reopen else 'command.json')).write_text(
            json.dumps({'argv': command, 'cwd': str(ROOT), 'entrypoint': 'runpy tikrec.pilot __main__',
                        'secret': 'generated test secret supplied by stdin; omitted'}))
        self.process = subprocess.Popen(command, cwd=ROOT, env=environment,
            stdin=subprocess.PIPE, stdout=self.stream, stderr=subprocess.STDOUT)
        self.process.stdin.write((SECRET + '\n').encode())
        self.process.stdin.close()

    @staticmethod
    def source_hash():
        """Bind test launch to exact current normalized source, not a stale revision alone."""
        hashes = {p.name: hashlib.sha256(p.read_bytes().replace(b'\r\n', b'\n')).hexdigest()
                  for p in sorted((ROOT / 'tikrec').glob('*.py'))}
        return hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()

    def events(self):
        """Read complete bounded launcher receipts, without manufacturing state."""
        events = []
        for line in self.log.read_text(encoding='utf-8', errors='replace').splitlines():
            try:
                value = json.loads(line)
                if isinstance(value, dict) and 'event' in value:
                    events.append(value)
            except ValueError:
                pass
        return events

    def ready(self):
        """Require actual bind/composition success and runtime provenance."""
        def condition():
            if self.process.poll() is not None:
                assert False, self.log.read_text(errors='replace')
            return any(e['event'] == 'ready' for e in self.events())
        wait(condition)
        value = next(e for e in self.events() if e['event'] == 'ready')
        assert value['checkout'] == str(ROOT) and value['schema'] == 10
        self.client = RemoteClient('http://127.0.0.1:' + str(value['port']), token=SECRET)
        return value

    def control(self, command):
        """Write one explicit local cleanup/shutdown operation; never signal arbitrary PIDs."""
        with (self.home / 'control.json').open('w', encoding='utf-8') as stream:
            json.dump({'operation': str(uuid4()), 'command': command}, stream)

    def finish(self, expected=0):
        """Confirm process exit, truthful last retirement receipt and no logged secret."""
        assert self.process.wait(timeout=90) == expected, self.log.read_text(errors='replace')
        self.stream.close()
        assert SECRET not in self.log.read_text(errors='replace')
        shutdown = [e for e in self.events() if e['event'] == 'shutdown']
        if shutdown:
            assert shutdown[-1]['complete']
        return shutdown

    def start(self, name, raw=False):
        """Start manually over authenticated native loopback with the normal HTTP shape."""
        return self.client.start('https://www.tiktok.com/@fixture.' + name.replace('-', '') + '/live',
            str(self.home / 'media' / (name + '.mp4')), raw_copy=raw)


def validate(parts, base):
    """Run normal deep validation read-only and preserve original file hashes."""
    paths = [p for p in parts.rglob('*') if p.is_file()]
    before = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    result = subprocess.run([sys.executable, '-m', 'tikrec.cli', 'validate', str(parts),
        '--deep', '--json'], cwd=ROOT, text=True, capture_output=True, timeout=60)
    (base / (parts.stem + '-validation.json')).write_text(json.dumps({
        'returncode': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr,
        'original_hashes': before}), encoding='utf-8')
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert all(hashlib.sha256(Path(path).read_bytes()).hexdigest() == sha for path, sha in before.items())
