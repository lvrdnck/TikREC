"""Shutdown-only original refusal proof and controls around real Windows owners."""

import os
from threading import Event

import pytest

from tests.service_runtime_helpers import runtime_case, managed_process, start, wait_for, hashes
from tests.test_release_recovery_windows_close import protection
from tikrec.flv import FlvFormatError
from tikrec.recording import RecordingBusy
from tikrec.session_journal_types import JournalConflict

pytestmark = pytest.mark.skipif(os.name != 'nt', reason='native Windows refusal ownership')


def refused(case, **options):
    """Refuse a generated admitted source before any usable configuration or part opening."""
    primary = FlvFormatError('generated early FLV refusal')
    case.failures['refused'] = primary
    runtime = case.build(authority_cleanup_guards=True, **options).start_runtime()
    accepted = start(runtime, 'refused')
    sid = accepted['session_id']
    wait_for(lambda: runtime.captures[sid]['done'])
    return runtime, accepted, primary


def assert_originals(runtime, sid, row, status, original):
    """Require the whole unfinished row/unit/binding and every original evidence byte."""
    assert runtime.journal.session(sid) == row and runtime.journal.status() == status
    assert row['phase'] == 'closing' and row['seal'] is None and row['task'] is None
    assert len(status['units']) == 1 and any(b['session'] == sid for b in status['bindings'])
    assert hashes(runtime.root) == original and not (runtime.root / 'refused.mp4').exists()


def test_early_source_refusal_repeated_shutdown_preserves_durable_failure(runtime_case):
    runtime, value, primary = refused(runtime_case)
    sid = value['session_id']
    bridge = runtime.captures[sid]['bridge']
    row, status, original = runtime.journal.session(sid), runtime.journal.status(), hashes(runtime.root)
    failure = bridge.failure
    assert failure.__cause__ is primary and not row['stop']
    result = runtime.shutdown()
    assert result['complete'] and result['captures_joined'] and result['finalizer_joined']
    assert runtime.shutdown() is result
    assert bridge.failure is failure and runtime.capture_errors[sid].original is failure
    assert bridge.lease.closed and not bridge.lease.handle.guard.retained
    assert all(not g.retained for g in runtime.authority.native_close_guards)
    assert all(not g.retained for g in bridge.fence.inputs.native_close_guards)
    assert not runtime.connections.has_ownership()
    assert_originals(runtime, sid, row, status, original)
    with pytest.raises(RecordingBusy):
        start(runtime, 'late', room='456')
    with pytest.raises(JournalConflict):
        bridge.fence.wrap(lambda: None)()


@pytest.mark.parametrize('resource', ['state', 'catalog', 'media', 'owner'])
def test_refusal_authority_native_close_fault_remains_reachable_until_exact_retry(runtime_case, resource):
    runtime, value, primary = refused(runtime_case)
    sid = value['session_id']
    row, status, original = runtime.journal.session(sid), runtime.journal.status(), hashes(runtime.root)
    owner = getattr(runtime.authority, resource)
    failure = runtime.captures[sid]['bridge'].failure
    assert failure.__cause__ is primary
    guard = owner.handle.guard if resource == 'owner' else owner.cleanup_guard
    handle = guard.original
    protection(handle, True)
    try:
        first = runtime.shutdown()
        assert not first['complete'] and first['captures_joined'] and first['finalizer_joined']
        assert runtime.connections.closing and guard.retained
        assert runtime.captures[sid]['refusal_retired']
        assert not runtime.shutdown()['complete'] and guard.retained
        # No journal borrower is admitted while the original catalog is closing.
        assert not runtime.connections.has_ownership()
        with pytest.raises(ValueError, match='closing'):
            runtime.journal.status()
    finally:
        protection(handle, False)
    assert runtime.shutdown()['complete'] and not guard.retained
    assert runtime.errors and runtime.captures[sid]['bridge'].failure is failure
    assert_originals(runtime, sid, row, status, original)


def test_stale_generation_cannot_retire_original_refusal_lease(runtime_case):
    runtime, value, _ = refused(runtime_case)
    sid = value['session_id']
    bridge = runtime.captures[sid]['bridge']
    row, status, original = runtime.journal.session(sid), runtime.journal.status(), hashes(runtime.root)
    generation = bridge.binding['generation']
    bridge.binding['generation'] += 1  # Trusted fixture presents a stale local generation, never SQL.
    assert not runtime.shutdown()['complete']
    assert not bridge.lease.closed and bridge.lease.handle.guard.retained
    assert_originals(runtime, sid, row, status, original)
    bridge.binding['generation'] = generation
    assert runtime.shutdown()['complete']
    assert_originals(runtime, sid, row, status, original)


@pytest.mark.parametrize('thread', ['caller', 'worker'])
def test_refusal_waits_for_original_thread_sqlite_close_retry(runtime_case, monkeypatch, thread):
    """A quiescent source does not authorize foreign-thread SQLite cleanup or lease release."""
    from threading import get_ident
    from tests.manifest_fence_helpers import ConnectionFaults
    runtime, value, _ = refused(runtime_case, shutdown_grace=0)
    sid = value['session_id']
    bridge = runtime.captures[sid]['bridge']
    row, status, original = runtime.journal.session(sid), runtime.journal.status(), hashes(runtime.root)
    connector, retained, creator = runtime.connections.original, [], get_ident()
    primary = OSError('generated original SQLite close fault')
    def connect():
        connection = connector()
        if not retained and ((get_ident() == creator) == (thread == 'caller')):
            connection = ConnectionFaults(connection, close=primary)
            retained.append(connection)
        return connection
    monkeypatch.setattr(runtime.connections, 'original', connect)
    if thread == 'caller':
        assert runtime.health()['active_count'] is None
    else:
        runtime.wake.set()
        wait_for(lambda: runtime.connections.failed(runtime))
    assert not runtime.shutdown()['complete']
    assert not bridge.lease.closed and bridge.lease.handle.guard.retained
    borrowers = tuple(runtime.connections.connections.values())
    assert len(borrowers) == 1 and borrowers[0].owner.connection is not None
    assert borrowers[0].thread == (creator if thread == 'caller' else runtime.worker.ident)
    retained[0].close_error = None  # Remove only this generated creator-thread fault.
    assert runtime.shutdown()['complete'] and not runtime.connections.has_ownership()
    assert primary in runtime.errors
    assert_originals(runtime, sid, row, status, original)


def test_unknown_source_close_cannot_be_reclassified_as_safe_refusal(runtime_case):
    case = runtime_case
    ready, release = case.hold('refused')
    case.failures['refused'] = FlvFormatError('original input failure')
    runtime = case.build(authority_cleanup_guards=True).start_runtime()
    source_options = runtime.observations
    secondary = OSError('generated unconfirmed source close')
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
        values = source_options(bridge)
        original = values['raw_tag_source']
        values['raw_tag_source'] = lambda url, raw: Source(original(url, raw))
        return values
    runtime.observations = options
    value = start(runtime, 'refused')
    assert ready.wait(10)
    release.set()
    sid = value['session_id']
    wait_for(lambda: runtime.captures[sid]['done'])
    bridge = runtime.captures[sid]['bridge']
    row, status, original = runtime.journal.session(sid), runtime.journal.status(), hashes(runtime.root)
    assert secondary in bridge.fence.cleanup_errors
    assert bridge.failure is case.failures['refused']
    assert not runtime.shutdown()['complete'] and not runtime.shutdown()['complete']
    assert not bridge.lease.closed and bridge.lease.handle.guard.retained
    assert_originals(runtime, sid, row, status, original)
    # Independent disposable fixture teardown remains separate from product confirmation.


def test_live_writer_and_callback_must_actually_join_before_retirement(runtime_case):
    case = runtime_case
    entered, release = Event(), Event()
    case.releases.append(release)
    runtime = case.build(authority_cleanup_guards=True, shutdown_grace=0).start_runtime()
    source_options = runtime.observations
    def progress(message):
        if message.startswith('part started:'):
            entered.set()
            assert release.wait(30)
    runtime.observations = lambda bridge: {**source_options(bridge), 'progress': progress}
    value = start(runtime, 'writer')
    assert entered.wait(10)
    sid = value['session_id']
    bridge = runtime.captures[sid]['bridge']
    assert bridge.fence.writer_openings and bridge.fence.inflight
    result = runtime.shutdown()
    assert not result['complete'] and not result['captures_joined']
    assert not bridge.lease.closed and bridge.lease.handle.guard.retained
    release.set()
    wait_for(lambda: runtime.captures[sid]['done'])
    assert runtime.shutdown()['complete']
    assert runtime.journal.session(sid)['phase'] == 'queued'
    assert 'refusal_retired' not in runtime.captures.get(sid, {})


def test_refusal_plus_disjoint_capture_stops_joins_without_draining_fifo(runtime_case):
    case = runtime_case
    ready, release = case.hold('healthy')
    case.cooperative.add('healthy')
    runtime = case.build(authority_cleanup_guards=True).start_runtime()
    healthy = start(runtime, 'healthy', room='456', creator='example.second')
    assert ready.wait(10)
    case.failures['refused'] = FlvFormatError('generated disjoint preconfiguration refusal')
    value = start(runtime, 'refused')
    sid = value['session_id']
    wait_for(lambda: runtime.captures[sid]['done'])
    row, original = runtime.journal.session(sid), hashes(runtime.root / 'refused.parts')
    assert runtime.shutdown()['complete']
    assert runtime.journal.session(sid) == row
    assert hashes(runtime.root / 'refused.parts') == original
    other = runtime.journal.session(healthy['session_id'])
    assert other['phase'] == 'queued' and other['stop'] and other['seal'] is not None
    assert len(runtime.journal.status()['units']) == 2
    assert not runtime.worker.is_alive() and not any(e['thread'].is_alive() for e in runtime.captures.values())
    assert not (runtime.root / 'healthy.mp4').exists()


def test_confirmed_h_race_keeps_queued_unit_and_cannot_use_refusal_permission(runtime_case):
    case = runtime_case
    ready, release_source = case.hold('held-h')
    entered, release = Event(), Event()
    case.releases.append(release)
    runtime = case.build(authority_cleanup_guards=True, shutdown_grace=0).start_runtime()
    value = start(runtime, 'held-h')
    assert ready.wait(10)
    bridge = runtime.captures[value['session_id']]['bridge']
    def fault(point):
        if point == 'confirmed_h':
            entered.set()
            assert release.wait(30)
    bridge._fault = fault
    release_source.set()
    assert entered.wait(30)
    row = runtime.journal.session(value['session_id'])
    assert row['phase'] == 'queued' and row['seal'] is not None
    assert not runtime.shutdown()['complete'] and not bridge.lease.closed
    release.set()
    wait_for(lambda: runtime.captures[value['session_id']]['done'])
    assert runtime.shutdown()['complete']
    assert runtime.journal.session(value['session_id']) == row
    assert len(runtime.journal.status()['units']) == 1
