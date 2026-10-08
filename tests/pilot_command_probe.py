"""Trusted offline source/fault seams around the actual python -m tikrec.pilot entrypoint."""
import getpass
import hashlib
import json
import os
import runpy
import shutil
import sys
import time
from pathlib import Path
from threading import current_thread, get_ident

BASE = Path(os.environ['TIKREC_PILOT_TEST_FIXTURES'])
MODE = os.environ.get('TIKREC_PILOT_TEST_MODE', 'copy')
original_usage = shutil.disk_usage

def usage(path):
    """Inject read-only free-space observations without filling a disk."""
    free = BASE / 'free.txt'
    actual = original_usage(path)
    return actual if not free.exists() else actual._replace(free=int(free.read_text()))

shutil.disk_usage = usage
# Generated test secret arrives on stdin only; never an argument or log value.
getpass.getpass = lambda _: sys.stdin.readline().strip()

from tikrec import pilot_composition
from tikrec.media import inspect_media
from tikrec.service_runtime import IsolatedServiceRuntime
from tikrec.tiktok import _ResolvedLiveUrl, TikTokOfflineError, TikTokResolutionTransientError


def supplied(envelope, bridge, ffprobe):
    """Fixture bytes still use the pilot's exact limiter/parser/writer/HTTP pipeline."""
    name = Path(bridge.intent.output_path).stem
    room = str(1000 + sum(map(ord, name)))
    files = [BASE / 'one.flv']
    if name == 'old' or MODE == 'policy':
        files.append(BASE / ('two.flv' if MODE == 'libx264' else 'one.flv'))
    actions = iter([*[_ResolvedLiveUrl('https://fixture.invalid/offline.flv', 2, room_id=room)
                       for _ in files], *[TikTokOfflineError('fixture ended', 4, room_id=room) for _ in range(3)]])
    if MODE == 'policy':
        live = _ResolvedLiveUrl('https://fixture.invalid/offline.flv', 2, room_id=room)
        offline = TikTokOfflineError('fixture ended', 4, room_id=room)
        actions = iter([live, offline, TikTokResolutionTransientError('fixture transient'),
                        live, offline, offline, offline])
    sources = iter(files)
    observations, delays = [], []
    def save():
        (BASE / (name + '-policy.json')).write_text(json.dumps({
            'observations': observations, 'delays': delays}))
    def waiter(event, seconds):
        # Accelerate only the fixture's cancellable wait, retaining requested policy values.
        delays.append(seconds)
        save()
        if MODE == 'policy' and len(delays) == 2:
            (BASE / 'offline-unconfirmed').write_text('original confirmation wait')
            while not (BASE / 'confirm-continue').exists() and not event.is_set():
                time.sleep(0.01)

    def resolver(_):
        value = next(actions)
        observations.append(type(value).__name__ if isinstance(value, Exception) else 'live:' + value.room_id)
        save()
        if isinstance(value, Exception):
            raise value
        return value
    def chunks(_, check):
        data = next(sources).read_bytes()
        half = len(data) // 2
        for offset in range(0, len(data), 256):
            check()
            if name.startswith('writer') and offset >= half and not (BASE / (name + '-half')).exists():
                (BASE / (name + '-half')).write_text('ready')
                while not (BASE / (name + '-continue')).exists():
                    check()
                    time.sleep(0.01)
            yield data[offset:offset + 256]
            time.sleep(0.02 if name.startswith('writer') else 0.001)
    return {**envelope.source_options(bridge, chunks=chunks, resolver=resolver),
            'media_inspector': lambda path: inspect_media(path, ffprobe=str(ffprobe)),
            'recovery_waiter': waiter}

pilot_composition.source_options = supplied


if MODE == 'startup-native-close':
    from tikrec.capture_handoff_native import NativeHandle
    from tests.test_release_recovery_windows_close import protection
    information, original_close = NativeHandle._information, NativeHandle.close
    blocked = []
    def fail_information(held):
        """Fail one newly guarded native constructor while its exact handle is protected."""
        if not blocked and held.path == BASE / 'pilot-home' / 'media' and hasattr(held, 'cleanup_guard'):
            blocked.append(held)
            protection(held.handle, True)
            raise ValueError('generated original startup proof failure')
        return information(held)
    def repair_close(held):
        """Remove only the generated exact-handle fault on explicit fixture repair."""
        if blocked and held is blocked[0] and held.handle is not None and (BASE / 'repair').exists():
            protection(held.handle, False)
        return original_close(held)
    NativeHandle._information, NativeHandle.close = fail_information, repair_close


class ProbeRuntime(IsolatedServiceRuntime):
    """Observe existing worker phases and inject one exact original-thread close failure."""

    def __init__(self, *args, **kwargs):
        kwargs['settlement_options'] = {**kwargs.get('settlement_options', {}), 'fault': self.fault}
        if MODE == 'writer-cap':
            kwargs['settlement_options']['candidate_limit_bytes'] = 131072
        super().__init__(*args, **kwargs)
        self.request_faulted = False
        connector = self.connections.original
        def connect():
            connection = connector()
            if MODE == 'sqlite-close' and not self.request_faulted and current_thread().name == 'tikrec-isolated-http':
                self.request_faulted = True
                return RefusedClose(connection)
            return connection
        self.connections.original = connect

    def fault(self, point):
        adapter = self.current
        if adapter is None:
            return
        runner = adapter.coordinator
        name = Path(self.journal.session(runner.claimed['session_id'])['intent']['output_path']).stem
        if point == 'after_media_plan':
            from tests.service_runtime_helpers import hashes
            record = {'session': runner.claimed['session_id'], 'token': runner.token,
                'copy': adapter.manifest.publication.validation.assembly.plan.stream_copy,
                'hashes': {str(p): sha for p, sha in hashes(self.root / (name + '.parts'), adapter).items()},
                'h_operation': self.journal.owned_attempt(runner.token)['h_operation'],
                'h': self.journal.operation(self.journal.owned_attempt(runner.token)['h_operation']),
                'seal': self.journal.session(runner.claimed['session_id'])['seal']}
            (BASE / (name + '-plan.json')).write_text(json.dumps(record))
            if name == 'old' and MODE in {'copy', 'libx264'}:
                (BASE / 'held').write_text(point)
                deadline = time.monotonic() + 120
                while not (BASE / 'release').exists():
                    assert time.monotonic() < deadline
                    time.sleep(0.01)
        if name == 'old' and MODE == 'queued' and point == 'before_terminal_release':
            (BASE / 'held').write_text(point)
            deadline = time.monotonic() + 120
            while not (BASE / 'release').exists():
                if self.stopping.is_set():
                    (BASE / 'stopping').write_text('existing shutdown fence set')
                assert time.monotonic() < deadline
                time.sleep(0.01)
        if name == 'old' and MODE == 'prepared' and point == 'before_terminal_release':
            raise OSError('generated prepared-success boundary')
        if name == 'old' and MODE == 'unsupported' and point == 'after_claim':
            raise OSError('generated unsupported boundary')
        if MODE == 'writer-cap' and point == 'after_assembly_diagnostics':
            (BASE / 'writer-cap.json').write_text(json.dumps({
                'size': (runner.scratch.path / 'candidate.mp4').stat().st_size,
                'launch': runner.children[-1]['intent']}))
        if point == 'after_terminal_release':
            with (BASE / 'completion-order.jsonl').open('a') as stream:
                stream.write(json.dumps({'session': runner.claimed['session_id'], 'name': name}) + '\n')


class RefusedClose:
    """Delegate one real SQLite connection and prove cleanup stays on its creator."""

    def __init__(self, raw):
        self.raw, self.creator = raw, get_ident()

    def __getattr__(self, name):
        return getattr(self.raw, name)

    def close(self):
        assert get_ident() == self.creator
        with (BASE / 'sqlite-close-threads.jsonl').open('a') as stream:
            stream.write(json.dumps({'creator': self.creator, 'closer': get_ident(),
                                    'repaired': (BASE / 'repair').exists()}) + '\n')
        if not (BASE / 'repair').exists():
            raise OSError('generated request close refusal')
        self.raw.close()

pilot_composition.IsolatedServiceRuntime = ProbeRuntime
if __name__ == '__main__':
    sys.argv[0] = 'tikrec.pilot'
    runpy.run_module('tikrec.pilot', run_name='__main__')
