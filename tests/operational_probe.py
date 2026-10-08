"""Generated resolver/clock seams around the actual headless normal CLI entrypoint."""
import json
import os
import runpy
import shutil
import time
from pathlib import Path

BASE = Path(os.environ['TIKREC_OPERATIONAL_TEST_ROOT'])
MODE = os.environ.get('TIKREC_OPERATIONAL_TEST_MODE', 'normal')
original_usage = shutil.disk_usage


def usage(path):
    """Observe fixture pressure without consuming real disk headroom."""
    actual = original_usage(path)
    control = BASE / 'free.txt'
    if not control.exists():
        return actual
    text = control.read_text()
    if text == 'unknown':
        raise OSError('generated unavailable observation')
    return actual._replace(free=int(text))


shutil.disk_usage = usage
from tikrec import operational_composition
from tikrec.operational_source import source_options
from tikrec.service_runtime import IsolatedServiceRuntime
from tikrec.tiktok import _ResolvedLiveUrl, TikTokOfflineError
from tikrec.tiktok_identity import LiveResolution


def supplied(policy, bridge, ffprobe, retry_policy):
    """Use product raw/parser/writer plus generated same-room observations."""
    name = Path(bridge.intent.output_path).stem
    generated_clock = [time.time()]
    room = bridge.intent.expected_room or str(1000 + sum(map(ord, bridge.intent.creator)))
    connections = 2 if MODE == 'changed' else 1
    actions = iter([*[_ResolvedLiveUrl('https://fixture.invalid/source.flv', 2, room_id=room)
                     for _ in range(connections)],
                    *[TikTokOfflineError('generated end', 4, room_id=room) for _ in range(3)]])
    def resolver(_):
        value = next(actions)
        if isinstance(value, Exception):
            raise value
        return value
    files = iter(['one.flv', 'two.flv'])
    def chunks(_, check):
        source = BASE / ('long.flv' if name == 'long' else 'large.flv' if MODE == 'budget'
                         else next(files) if MODE == 'changed' else 'one.flv')
        with source.open('rb') as stream:
            while chunk := stream.read(65536):
                check()
                if 'writer' in name and not (BASE / 'release-source').exists():
                    (BASE / 'source-held').write_text('exact source remains running')
                    yield chunk
                    while not (BASE / 'release-source').exists():
                        check()
                        time.sleep(0.01)
                else:
                    yield chunk
        if name == 'long':
            # Accelerated source wall span is independent of the real subprocess duration.
            generated_clock[0] += 130
    result = {**source_options(policy, bridge, ffprobe, retry_policy, chunks=chunks, resolver=resolver),
              'recovery_waiter': lambda event, seconds: event.wait(0.001)}
    if name == 'long':
        result.update(clock=lambda: generated_clock[0], manifest_clock=lambda: generated_clock[0],
                      observation_clock=lambda: generated_clock[0])
    return result


operational_composition.source_options = supplied
if MODE == 'sink':
    from tikrec.operational_diagnostics import Diagnostics
    original_emit = Diagnostics.emit
    def emit(self, event, **values):
        """Fail a receipt only after a real start has produced UUID phase evidence."""
        if event == 'observation' and values.get('phase', [None, None])[1] == 'completed':
            raise OSError('generated diagnostic sink failure')
        return original_emit(self, event, **values)
    Diagnostics.emit = emit
OriginalMonitor = operational_composition.CreatorMonitor


def monitor(creators, **options):
    """Run real monitor cycles with generated public identities, never TikTok access."""
    def resolver(url):
        creator = url.split('@')[1].split('/')[0]
        room = str(1000 + sum(map(ord, creator)))
        return LiveResolution(room, 'https://fixture.invalid/source.flv', 2)
    return OriginalMonitor(creators, resolver=resolver, poll_interval=0.05, **options)


operational_composition.CreatorMonitor = monitor


class Runtime(IsolatedServiceRuntime):
    """Hold only generated phase barriers; product execution/ownership stays real."""

    def __init__(self, *args, **kwargs):
        kwargs['settlement_options'] = {**kwargs.get('settlement_options', {}), 'fault': self.fault}
        super().__init__(*args, **kwargs)

    def start_runtime(self):
        """Record real work startup so bind refusal cannot be confused with ready."""
        (BASE / 'work-started').touch()
        return super().start_runtime()

    def fault(self, point):
        if point == 'after_terminal_release':
            (BASE / 'registry.json').write_text(json.dumps({
                'guards': len(self.authority.native_close_guards), 'captures': len(self.captures),
                'attempts': len(self.authority._attempts)}))
        if MODE == 'budget' and point == 'after_media_plan':
            # Product budget derives from this physical-space observation, not a changed cap.
            (BASE / 'free.txt').write_text(str(3 * 1024**3 + 16 * 1024**2))
        if MODE == 'hold' and point == 'after_media_plan':
            (BASE / 'finalizer-held').write_text(point)
            while not (BASE / 'release-finalizer').exists():
                time.sleep(0.01)
        if MODE == 'prepared' and point == 'before_terminal_release':
            raise OSError('generated prepared-success boundary')
        if MODE == 'unsupported' and point == 'after_claim':
            raise OSError('generated unsupported boundary')


operational_composition.IsolatedServiceRuntime = Runtime
if __name__ == '__main__':
    runpy.run_module('tikrec.cli', run_name='__main__')
