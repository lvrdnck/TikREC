"""Observe real CLI ownership independently of deliberately broken product sinks."""
import json
import os
import runpy
import sys
import time
from threading import enumerate as threads, get_ident

from tests import operational_probe as generated
from tikrec import operational_command as command
from tikrec.capture_handoff_native import NativeHandle
from tikrec.operational_diagnostics import Diagnostics
from tikrec.release_recovery_handles import NativeCloseGuard
from tikrec.service_runtime_shutdown import authority_retired
from tikrec.session_journal_manifest_fence import ManifestFenceConnection
from tikrec.recording import RecordingBusy

BASE = generated.BASE
FAULT = os.environ.get('TIKREC_REPORT_FAULT', 'healthy')
STAGE = os.environ.get('TIKREC_REPORT_STAGE', 'ready')
RETENTION = os.environ.get('TIKREC_REPORT_OWNER', '')
console = sys.stdout
owner = None
primary = ValueError('generated primary; never product diagnostics')
blocked = None
reader = None


def record(event, **values):
    """Keep prospective test observations outside the failed product log/console."""
    with (BASE / 'witness.jsonl').open('a', encoding='utf-8') as stream:
        stream.write(json.dumps({'event': event, 'pid': os.getpid(), 'thread': get_ident(),
                                 **values}) + '\n')


def snapshot(event):
    """Observe original references, guards, borrowers and threads before process exit."""
    runtime = owner.runtime
    reporting = getattr(owner, 'reporting', None)
    fenced = None
    if runtime and runtime.closed:
        try:
            runtime.start('https://www.tiktok.com/@fixture.refused/live', runtime.root / 'refused.mp4')
        except RecordingBusy:
            fenced = True
        else:
            fenced = False
    record(event, owner=id(owner), primary_same=owner.primary is primary,
        primary_type=None if owner.primary is None else type(owner.primary).__name__,
        attached_same=getattr(owner.primary, 'scratch_native_owner', None) is blocked if blocked else None,
        result=owner.last_result, shutdown_requested=owner.shutdown_requested,
        pins=len(owner.state.pins), guards=sum(g.retained for g in owner.state.native_close_guards),
        authority_retired=authority_retired(runtime) if runtime else None,
        sqlite_owned=runtime.connections.has_ownership() if runtime else None,
        closed=runtime.closed if runtime else None,
        stopping=runtime.stopping.is_set() if runtime else None,
        admission_fenced=fenced,
        native_retained=blocked.handle is not None if blocked else False,
        reader_retained=reader.connection is not None if reader else False,
        reporting=[{'channel': c, 'type': type(e).__name__} for c, e in reporting.errors]
            if reporting else [],
        threads=[t.name for t in threads() if t is not __import__('threading').current_thread()])


class Console:
    """Fail actual Windows pipe writes or one controlled write/flush phase."""

    def __init__(self):
        self.failing = False

    def write(self, text):
        """Arm at the selected actual lifecycle receipt, then keep the channel failed."""
        try:
            event = json.loads(text)['event']
        except (ValueError, KeyError):
            event = None
        if event == STAGE and FAULT != 'healthy' and not self.failing:
            self.failing = True
            if FAULT == 'pipe':
                (BASE / 'close-pipe').touch()
                while not (BASE / 'pipe-closed').exists():
                    time.sleep(0.01)
        if self.failing:
            record('console-write', kind=FAULT)
            if FAULT == 'write':
                raise OSError('generated console write failure')
        return console.write(text)

    def flush(self):
        """Fail flush independently of successful writes."""
        if self.failing and FAULT == 'flush':
            record('console-flush')
            raise OSError('generated console flush failure')
        return console.flush()


sys.stdout = Console()
original_init = command.OperationalCommand.__init__
original_cleanup = command.OperationalCommand.cleanup
original_compose = command.compose
original_emit = Diagnostics.emit


def initialize(self, *args):
    """Retain the actual CLI supervisor rather than substituting a runtime."""
    global owner
    original_init(self, *args)
    owner = self
    record('owner-created', owner=id(self), source=command.__file__)


def cleanup(self):
    """Observe the product result even when its inherited console emission raises."""
    record('cleanup-enter', owner=id(self))
    try:
        return original_cleanup(self)
    finally:
        snapshot('cleanup-return')


class RefusedClose:
    """Hold an actual SQLite reader on its original supervisor thread."""

    def __init__(self, raw):
        self.raw, self.creator = raw, get_ident()

    def __getattr__(self, name):
        return getattr(self.raw, name)

    def close(self):
        """Permit only an explicit fixture repair, recording exact-thread closure."""
        record('reader-close', creator=self.creator, repaired=(BASE / 'repair').exists())
        assert self.creator == get_ident()
        if not (BASE / 'repair').exists():
            raise OSError('generated SQLite close refusal')
        self.raw.close()


def compose(self, *args):
    """Preserve real listener/monitor/worker startup before a generated primary fault."""
    global blocked, reader
    original_compose(self, *args)
    record('composed', port=self.server.server_port)
    if RETENTION == 'native':
        from tests.test_release_recovery_windows_close import protection
        blocked = NativeHandle(BASE / 'native-held.bin',
            cleanup_guard_factory=lambda h: NativeCloseGuard(self.state, h, resource_key='generated'))
        protection(blocked.handle, True)
        primary.scratch_native_owner = blocked
    if RETENTION == 'sqlite':
        reader = ManifestFenceConnection(RefusedClose(self.runtime.connections.original()))
        primary.manifest_fence_owner = reader
    if STAGE == 'failure' and not (BASE / 'supervision').exists():
        (BASE / 'disk-failed').touch()
        raise primary
    original_supervise = self.envelope.supervise
    def supervise(runtime):
        if (BASE / 'trigger').exists():
            raise primary
        return original_supervise(runtime)
    self.envelope.supervise = supervise


def emit(self, event, **values):
    """Fail the disk channel independently, preserving existing bounded logger otherwise."""
    if (BASE / 'disk-failed').exists():
        record('disk-write', receipt=event)
        raise OSError('generated disk log failure')
    return original_emit(self, event, **values)


original_native_close = NativeHandle.close
def native_close(held):
    """Repair only the exact test-held native object; never reopen/adopt its path."""
    if held is blocked and held.handle is not None and (BASE / 'repair').exists():
        from tests.test_release_recovery_windows_close import protection
        protection(held.handle, False)
    return original_native_close(held)


command.OperationalCommand.__init__ = initialize
command.OperationalCommand.cleanup = cleanup
command.compose = compose
Diagnostics.emit = emit
NativeHandle.close = native_close

original_phase = generated.Runtime.fault
def phase(self, point):
    """Hold eligible prepared release, with real writer/validation already retired."""
    if generated.MODE == 'hold' and point == 'after_media_plan':
        return  # This fixture holds a supported safe boundary, not unsealed scratch.
    if generated.MODE == 'hold' and point == 'before_terminal_release':
        (BASE / 'finalizer-held').touch()
        while not (BASE / 'release-finalizer').exists():
            time.sleep(0.01)
    return original_phase(self, point)


generated.Runtime.fault = phase


def rescue():
    """Separate baseline fixture intervention from product-owned shutdown proof."""
    if owner is None:
        return
    snapshot('escaped-owner')
    while not (BASE / 'rescue').exists():
        time.sleep(0.05)
    sys.stdout = console
    record('baseline-intervention', action='original-thread fixture cleanup')
    owner.primary = owner.primary if owner.primary is not None else primary
    owner.cleanup()
    snapshot('intervention-result')


if __name__ == '__main__':
    try:
        runpy.run_module('tikrec.cli', run_name='__main__')
    except SystemExit as exit:
        if owner:
            snapshot('product-exit')
            if owner.last_result is None and owner.state.pins or owner.last_result and not owner.last_result['complete']:
                record('escaped', type='SystemExit', code=exit.code)
                rescue()
        record('exit', code=exit.code)
        raise
    except BaseException as error:
        record('escaped', type=type(error).__name__)
        rescue()
        raise SystemExit(91)
