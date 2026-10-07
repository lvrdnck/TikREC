"""Actual partial thread startup must remain owned through confirmed shutdown."""

import os
from threading import Event, Thread

import pytest

pytestmark = pytest.mark.skipif(os.name != 'nt', reason='native Windows runtime')

from tests.service_runtime_helpers import runtime_case, managed_process, start, wait_for


def test_started_finalizer_with_lost_launch_ack_stays_tracked_and_blocks_safe_exit(runtime_case):
    """A real blocked native thread cannot be reported joined after startup fails."""
    case = runtime_case
    entered, release = Event(), Event()
    case.releases.append(release)
    first = OSError('finalizer started; launch acknowledgement lost')
    created = []
    class Partial(Thread):
        def start(self):
            super().start()
            raise first
    def factory(**options):
        target, args = options['target'], options['args']
        def held():
            entered.set()
            assert release.wait(30)
            target(*args)
        options.update(target=held, args=())
        thread = Partial(**options)
        created.append(thread)
        return thread
    runtime = case.build(thread_factory=factory, shutdown_grace=0)
    try:
        with pytest.raises(OSError) as error:
            runtime.start_runtime()
        assert error.value is first and runtime.errors[0] is first
        assert entered.wait(10)
        assert runtime.worker is created[0] and runtime.worker.is_alive()
        result = runtime.shutdown()
        assert not result['complete'] and not result['finalizer_joined']
        assert not result['authority_released'] and runtime.worker.is_alive()
        assert not runtime.journal.history()
        release.set()
        assert runtime.shutdown()['complete']
        assert not runtime.worker.is_alive()
    finally:
        release.set()


def test_started_capture_with_lost_launch_ack_remains_addressable_and_joined(runtime_case):
    """Keep a real writer's UUID/thread so targeted stop and H can finish safely."""
    case = runtime_case
    entered, release = case.hold('partial')
    case.cooperative.add('partial')
    first = OSError('capture started; launch acknowledgement lost')
    class Partial(Thread):
        def start(self):
            super().start()
            raise first
    def factory(**options):
        return Partial(**options) if options['name'].startswith('tikrec-isolated-capture') else Thread(**options)
    runtime = case.build(thread_factory=factory).start_runtime()
    with pytest.raises(OSError) as error:
        start(runtime, 'partial')
    assert error.value is first and runtime.errors[0] is first
    sid = runtime.latest[1]
    assert entered.wait(10)
    entry = runtime.captures[sid]
    assert entry['thread'] is not None and entry['thread'].is_alive() and not entry['done']
    assert len(runtime.journal.status()['units']) == 1
    runtime.stop(sid)
    assert entry['bridge'].stop_event.is_set()
    release.set()
    wait_for(lambda: runtime.session_status(sid)['output_completed'])
    assert not runtime.journal.status()['units']
    assert runtime.shutdown()['complete']
    assert not entry['thread'].is_alive()


def test_interrupted_start_without_confirmed_join_retains_catalog(runtime_case):
    """An interruption cannot establish that a constructed thread never started."""
    case = runtime_case
    first = KeyboardInterrupt('startup interrupted before confirmation')
    def factory(**options):
        thread = Thread(**options)
        thread.start = lambda: (_ for _ in ()).throw(first)
        return thread
    runtime = case.build(thread_factory=factory, shutdown_grace=0)
    with pytest.raises(KeyboardInterrupt) as error:
        runtime.start_runtime()
    assert error.value is first and runtime.errors[0] is first
    assert runtime.worker is not None and runtime.worker.ident is None
    result = runtime.shutdown()
    assert not result['complete'] and not result['finalizer_joined'] and not result['authority_released']
    # Independent fixture action retires this deliberately never-started object.
    # Its fenced target must exit without claiming any recording.
    Thread.start(runtime.worker)
    assert runtime.shutdown()['complete']
    assert not runtime.worker.is_alive() and not runtime.journal.history()
