"""Generated connected offline runtime fixtures and independent cleanup barriers."""

import hashlib
import shutil
import subprocess
import time
from pathlib import Path
from threading import Event
from types import SimpleNamespace

import pytest

from tests.capture_handoff_helpers import local_media, observations
from tests.owned_process_helpers import managed_process
from tests.journal_settlement_helpers import independent_cleanup
from tikrec.capture_handoff_authority import operation_id
from tikrec.service_runtime import IsolatedServiceRuntime
from tikrec.session_journal import SessionJournal
from tikrec.storage_status import StorageStatus, GIB
from tikrec.source import iter_tags
from tikrec.tiktok import _ResolvedLiveUrl, TikTokOfflineError


def wait_for(predicate, timeout=45):
    """Poll durable assertions within a fixture bound, never using sleep for ordering."""
    deadline = time.monotonic() + timeout
    while not predicate():
        assert time.monotonic() < deadline, 'runtime condition was not reached'
        time.sleep(0.01)


def start(runtime, name, room='123', creator='example.creator', raw=True):
    """Use the same public manual interface with a disposable output and room."""
    return runtime.start('https://www.tiktok.com/@' + creator + '/live',
        str(runtime.root / (name + '.mp4')), expected_room_id=room, raw_copy=raw)


def hashes(root, adapter=None):
    """Hash original media/control without later scratch or lifecycle lock bytes."""
    held = {} if adapter is None else {h.path: h for h in adapter.coordinator.guard.handles}
    return {p: hashlib.sha256(held[p].read_control() if p in held else p.read_bytes()).hexdigest()
            for p in root.rglob('*') if p.is_file() and p.name != '.tikrec-lifecycle.lock'}


def preserved(before, token):
    """Check originals through the accepted manifest predecessor preservation."""
    for path, expected in before.items():
        actual = path.parent / ('.tikrec-manifest-' + token + '.original.json') if path.name == 'session.json' else path
        assert hashlib.sha256(actual.read_bytes()).hexdigest() == expected


@pytest.fixture
def runtime_case(tmp_path, managed_process, monkeypatch):
    """Compose a real journal/capture/native settlement runtime with local sources."""
    state, root = tmp_path / 'state', tmp_path / 'media'
    state.mkdir()
    root.mkdir()
    journal = SessionJournal.initialize(state / 'sessions.sqlite3', operation_id())
    first = local_media(tmp_path / 'source-one.flv')
    second_path = tmp_path / 'source-two.flv'
    subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'testsrc=size=80x64:rate=10',
        '-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=44100', '-t', '0.6',
        '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-g', '3', '-c:a', 'aac', '-f', 'flv',
        str(second_path)], check=True, capture_output=True, timeout=30)
    case = SimpleNamespace(holds={}, releases=[], runtimes=[], failures={}, different=set(),
                           free=100 * GIB, fault=lambda _: None, adapters=[], cooperative=set())
    def source_options(bridge):
        name, room = Path(bridge.intent.output_path).stem, bridge.intent.expected_room
        entered, release = case.holds.get(name, (None, None))
        media = [first, second_path.read_bytes() if name in case.different else first]
        resolution = iter([_ResolvedLiveUrl('https://fixture.invalid/media.flv', 2, room_id=room),
                           _ResolvedLiveUrl('https://fixture.invalid/media.flv', 2, room_id=room),
                           TikTokOfflineError('fixture ended', room_id=room)])
        data = iter(media)
        def resolver(_):
            value = next(resolution)
            if isinstance(value, Exception):
                raise value
            return value
        def chunks(raw=None):
            value = next(data)
            if name in case.cooperative:
                if raw is not None:
                    raw.write(value)
                yield value
                entered.set()
                # Real tags have reached the writer before cooperative stop.
                while not release.wait(0.01) and not bridge.stop_event.is_set():
                    pass
                if raw is not None:
                    raw.observe_read_end('eof')
                return
            if entered is not None:
                entered.set()
                assert release.wait(45), 'capture release missing'
            if name in case.failures:
                raise case.failures[name]
            if raw is not None:
                raw.write(value)
                raw.observe_read_end('eof')
            yield value
        result = observations(first, room=room)
        result.update(resolver=resolver, tag_source=lambda _: iter_tags(chunks()),
                      raw_tag_source=lambda _, raw: iter_tags(chunks(raw)))
        return result
    def create(sid, token):
        owner = managed_process()
        owner.session_id, owner.attempt_token = sid, token
        return owner
    def build(**options):
        storage = StorageStatus(root, disk_usage=lambda _: SimpleNamespace(free=case.free))
        runtime = IsolatedServiceRuntime(journal, root,
            ffmpeg=Path(shutil.which('ffmpeg')).resolve(), ffprobe=Path(shutil.which('ffprobe')).resolve(),
            storage_status=storage, observations=source_options,
            settlement_options={'process_factory': create, 'fault': lambda p: case.fault(p)},
            poll_interval=0.05, **options)
        case.runtimes.append(runtime)
        return runtime
    def hold(name):
        pair = Event(), Event()
        case.holds[name] = pair
        case.releases.append(pair[1])
        return pair
    case.build, case.hold = build, hold
    yield case
    for release in case.releases:
        release.set()
    case.fault = lambda _: None
    monkeypatch.undo()
    for runtime in case.runtimes:
        for connection in tuple(runtime.connections.connections.values()):
            if hasattr(connection.raw, 'close_error'):
                connection.raw.close_error = connection.raw.rollback_error = None
        # An independent fixture cleanup is executed on the worker's own thread.
        from tikrec import service_runtime_worker
        original = service_runtime_worker.cleanup_current
        def independent(value):
            for runner in tuple(value.authority._attempts.values()):
                adapter = SimpleNamespace(coordinator=runner,
                    capability=getattr(runner, 'settlement_owner', None))
                try:
                    independent_cleanup(adapter)
                    runner.closed = True
                finally:
                    # An earlier native close can leave a non-closed FileIO object.
                    # Keep it supervised until this independent fixture can prove
                    # its CRT slot empty, before releasing its Python metadata.
                    lease = None if runner.guard is None else runner.guard.lifecycle
                    stream = None if lease is None else lease.handle
                    guard = getattr(stream, 'guard', None)
                    if guard is not None and not guard.retained and not stream.closed:
                        import msvcrt
                        with pytest.raises(OSError):
                            msvcrt.get_osfhandle(guard.descriptor)
                        try:
                            stream.raw.close()
                        except OSError:
                            pass
                        assert stream.closed
            for owner in tuple(value.authority._recovery_owners.values()):
                for reader in owner.readers:
                    connection = reader.connection
                    if connection is not None and hasattr(connection, 'close_error'):
                        connection.close_error = connection.rollback_error = None
                owner.close()
            original(value)
        monkeypatch.setattr(service_runtime_worker, 'cleanup_current', independent)
        runtime.cleanup_requested.set()
        runtime.wake.set()
        result = runtime.shutdown()
        assert result['finalizer_joined'] and result['captures_joined'], result
        if not runtime.authority_closed:
            # Exact disposable objects remain reachable even after ExitStack failure.
            for held in (runtime.authority.state, runtime.authority.catalog, runtime.authority.media):
                held.close()
            runtime.authority.close()
            runtime.connections.restore()
        monkeypatch.undo()
