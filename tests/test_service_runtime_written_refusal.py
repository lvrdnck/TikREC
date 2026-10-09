"""Written pre-H failures must retire original owners without settling evidence."""

import os

import pytest

from tests.service_runtime_helpers import runtime_case, managed_process, start, wait_for, hashes
from tikrec.tiktok import _ResolvedLiveUrl

pytestmark = pytest.mark.skipif(os.name != 'nt', reason='exact Windows cleanup proof')


def written_failure(case, *, raw=True, observer=False):
    """Write generated media, then exhaust resolution or fail a fenced observer."""
    runtime = case.build(authority_cleanup_guards=True).start_runtime()
    original = runtime.observations
    primary = RuntimeError('generated observer failure after written part')
    def options(bridge):
        values = original(bridge)
        resolution = iter([_ResolvedLiveUrl('https://fixture.invalid/media.flv', 2,
                                           room_id=bridge.intent.expected_room)])
        values['resolver'] = lambda _: next(resolution)
        if observer:
            def progress(message):
                if message.startswith('connection lost:'):
                    raise primary
            values['progress'] = progress
        return values
    runtime.observations = options
    accepted = start(runtime, 'written', raw=raw)
    sid = accepted['session_id']
    wait_for(lambda: runtime.captures[sid]['done'])
    return runtime, sid, primary


@pytest.mark.parametrize('raw,observer', [(True, False), (False, False), (True, True)])
def test_written_failure_retires_without_h_or_accounting_change(runtime_case, raw, observer):
    runtime, sid, primary = written_failure(runtime_case, raw=raw, observer=observer)
    bridge = runtime.captures[sid]['bridge']
    assert bridge.fence.writer_openings > 0
    assert tuple(runtime.root.glob('written.parts/part*.flv'))
    row, status, original = runtime.journal.session(sid), runtime.journal.status(), hashes(runtime.root)
    failure = bridge.failure
    assert row['phase'] == 'closing' and row['seal'] is None and row['task'] is None
    if observer:
        assert failure is primary
    else:
        assert isinstance(failure.__cause__, StopIteration)
    result = runtime.shutdown()
    assert result['complete'] and result['captures_joined'] and result['finalizer_joined']
    assert runtime.shutdown() is result
    assert bridge.failure is failure and bridge.fence.writer_openings > 0
    assert bridge.lease.closed and not bridge.lease.handle.guard.retained
    import json
    assert json.loads(json.dumps(runtime.captures[sid]['refusal_retired']))['writer_openings'] > 0
    assert hashes(runtime.root) == original
    assert runtime.journal.session(sid) == row and runtime.journal.status() == status
    assert runtime.journal.operation(bridge.handoff_operation) is None
    assert not (runtime.root / 'written.mp4').exists()
    fresh = runtime_case.build(authority_cleanup_guards=True).start_runtime()
    assert fresh.session_status(sid)['needs_attention'] and fresh.captures == {}
    assert fresh.shutdown()['complete']
    assert fresh.journal.session(sid) == row and fresh.journal.status() == status
    assert hashes(runtime.root) == original


@pytest.mark.parametrize('resource', ['capture_part', 'capture_control'])
def test_written_native_close_fault_requires_exact_explicit_retry(runtime_case, resource):
    from tests.test_release_recovery_windows_close import protection
    from tikrec.capture_writer_owners import CaptureWriterOwners
    protected = []
    original_open = CaptureWriterOwners.open
    # Protect only one original test handle, never a process or unrelated file.
    def opening(self, path, mode, **options):
        stream = original_open(self, path, mode, **options)
        guard = self.streams[-1]['guard']
        if guard.resource_key == resource and self.parts_opened and not protected:
            protection(guard.original, True)
            protected.append(guard.original)
        return stream
    from unittest.mock import patch
    with patch.object(CaptureWriterOwners, 'open', opening):
        runtime, sid, _ = written_failure(runtime_case)
    bridge = runtime.captures[sid]['bridge']
    failure = bridge.failure
    row, status, original = runtime.journal.session(sid), runtime.journal.status(), hashes(runtime.root)
    try:
        assert protected and not runtime.shutdown()['complete']
        assert not runtime.shutdown()['complete'] and not bridge.lease.closed
        assert bridge.fence.writers.streams and bridge.failure is failure
    finally:
        for handle in protected:
            protection(handle, False)
    assert runtime.shutdown()['complete']
    assert bridge.fence.writers.retired() and bridge.fence.writer_openings > 0
    assert bridge.fence.writers.errors and runtime.errors
    assert bridge.failure is failure
    assert runtime.journal.session(sid) == row and runtime.journal.status() == status
    assert hashes(runtime.root) == original


@pytest.mark.parametrize('ambiguity', ['generation', 'pending', 'marker', 'writer_generation'])
def test_written_stale_or_ambiguous_owner_cannot_release_original_lease(runtime_case, ambiguity):
    from pathlib import Path
    from tikrec.capture_handoff_marker import MARKER_NAME
    runtime, sid, _ = written_failure(runtime_case)
    bridge = runtime.captures[sid]['bridge']
    if ambiguity == 'generation':
        bridge.binding['generation'] += 1
    elif ambiguity == 'writer_generation':
        bridge.fence.writers.generation += 1
    elif ambiguity == 'pending':
        runtime.authority.pending.add(sid)
    else:
        (Path(bridge.intent.parts_path) / MARKER_NAME).write_text('ambiguous fixture marker')
    row, status, original = runtime.journal.session(sid), runtime.journal.status(), hashes(runtime.root)
    assert not runtime.shutdown()['complete'] and not bridge.lease.closed
    assert bridge.lease.handle.guard.retained
    assert runtime.journal.session(sid) == row and runtime.journal.status() == status
    assert hashes(runtime.root) == original
    # Independent fixture teardown owns these disposable references; no product adoption.


def test_written_failure_waits_for_original_sqlite_close_retry(runtime_case, monkeypatch):
    from tests.manifest_fence_helpers import ConnectionFaults
    runtime, sid, _ = written_failure(runtime_case)
    bridge = runtime.captures[sid]['bridge']
    connector, retained = runtime.connections.original, []
    primary = OSError('written failure original SQLite close fault')
    def connect():
        connection = connector()
        if not retained:
            connection = ConnectionFaults(connection, close=primary)
            retained.append(connection)
        return connection
    monkeypatch.setattr(runtime.connections, 'original', connect)
    runtime.health()
    assert not runtime.shutdown()['complete'] and not bridge.lease.closed
    retained[0].close_error = None
    assert runtime.shutdown()['complete']
    assert primary in runtime.errors


def test_written_proof_survives_sealed_catalog_cleanup_retry(runtime_case):
    from tests.test_release_recovery_windows_close import protection
    runtime, sid, _ = written_failure(runtime_case)
    bridge = runtime.captures[sid]['bridge']
    row, status, original = runtime.journal.session(sid), runtime.journal.status(), hashes(runtime.root)
    guard = runtime.authority.catalog.cleanup_guard
    handle = guard.original
    protection(handle, True)
    try:
        assert not runtime.shutdown()['complete'] and runtime.connections.closing
        assert runtime.captures[sid]['refusal_writer_owner'] is bridge.fence.writers
        assert bridge.fence.writers.retired() and bridge.lease.closed
        assert not runtime.shutdown()['complete'] and guard.retained
    finally:
        protection(handle, False)
    assert runtime.shutdown()['complete'] and not guard.retained
    assert runtime.journal.session(sid) == row and runtime.journal.status() == status
    assert hashes(runtime.root) == original


def test_written_unknown_source_close_is_not_a_known_writer_diagnostic(runtime_case):
    runtime = runtime_case.build(authority_cleanup_guards=True).start_runtime()
    original = runtime.observations
    secondary = OSError('written source close remains unconfirmed')
    class Source:
        def __init__(self, iterator):
            self.iterator = iter(iterator)
        def __iter__(self):
            return self
        def __next__(self):
            return next(self.iterator)
        def close(self):
            self.iterator.close()
            raise secondary
    def options(bridge):
        values = original(bridge)
        source = values['raw_tag_source']
        values['raw_tag_source'] = lambda url, raw: Source(source(url, raw))
        return values
    runtime.observations = options
    sid = start(runtime, 'unknown')['session_id']
    wait_for(lambda: runtime.captures[sid]['done'])
    bridge = runtime.captures[sid]['bridge']
    assert bridge.fence.writer_openings and bridge.fence.writers.retired()
    assert secondary in bridge.fence.cleanup_errors
    row, status, original = runtime.journal.session(sid), runtime.journal.status(), hashes(runtime.root)
    assert not runtime.shutdown()['complete'] and not runtime.shutdown()['complete']
    assert not bridge.lease.closed and bridge.lease.handle.guard.retained
    assert runtime.journal.session(sid) == row and runtime.journal.status() == status
    assert hashes(runtime.root) == original


def test_written_failure_and_disjoint_healthy_capture_keep_both_units(runtime_case):
    case = runtime_case
    ready, _ = case.hold('healthy')
    case.cooperative.add('healthy')
    runtime, sid, _ = written_failure(case)
    # A new session uses the fixture's normal confirmed-end resolver, not the failure seam.
    failure_options = runtime.observations
    def options(bridge):
        values = failure_options(bridge)
        if bridge.intent.expected_room == '456':
            from tikrec.tiktok import TikTokOfflineError
            def ended(_):
                raise TikTokOfflineError('fixture ended', room_id='456')
            resolution = iter([_ResolvedLiveUrl('https://fixture.invalid/media.flv', 2, room_id='456')])
            def resolver(page):
                return next(resolution) if not bridge.stop_event.is_set() else ended(page)
            values['resolver'] = resolver
        return values
    runtime.observations = options
    healthy = start(runtime, 'healthy', room='456', creator='example.second')
    assert ready.wait(10)
    row, original = runtime.journal.session(sid), hashes(runtime.root / 'written.parts')
    assert runtime.shutdown()['complete']
    assert runtime.journal.session(sid) == row and hashes(runtime.root / 'written.parts') == original
    other = runtime.journal.session(healthy['session_id'])
    assert other['phase'] == 'queued' and other['seal'] is not None and other['stop']
    assert len(runtime.journal.status()['units']) == 2
