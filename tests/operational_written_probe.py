"""Prospective witnesses around the actual CLI's generated written failure."""

import hashlib
import json
import os
import runpy
from pathlib import Path
from threading import current_thread, enumerate as threads, get_ident

from tests import operational_probe as generated
from tikrec import operational_command, service_runtime_capture
from tikrec.recording import RecordingBusy
from tikrec.service_runtime_shutdown import authority_retired

BASE = generated.BASE
original_options = generated.supplied
original_capture = service_runtime_capture.run_capture
original_cleanup = operational_command.OperationalCommand.cleanup
protected = None


def record(event, **values):
    """Persist observations independently of product output and before CLI return."""
    with (BASE / 'written-witness.jsonl').open('a', encoding='utf-8') as stream:
        stream.write(json.dumps({'event': event, 'pid': os.getpid(), 'thread': get_ident(),
                                 **values}, default=str) + '\n')


def supplied(policy, bridge, ffprobe, retry_policy):
    """Keep product ingestion; only the generated resolver exhausts after its written EOF."""
    values = original_options(policy, bridge, ffprobe, retry_policy)
    resolver = values['resolver']
    called = False
    def once(page):
        nonlocal called
        if called:
            raise StopIteration('generated resolver exhausted after written EOF')
        called = True
        return resolver(page)
    values['resolver'] = once
    return values


def capture(runtime, sid, generation):
    """Witness completed failed execution without replacing its result or cleanup."""
    try:
        return original_capture(runtime, sid, generation)
    finally:
        bridge = runtime.captures[sid]['bridge']
        parts = Path(bridge.intent.parts_path)
        record('capture-return', session=sid, generation=generation, owner=id(bridge),
            row=runtime.journal.session(sid), status=runtime.journal.status(),
            failure=id(bridge.failure), failure_type=type(bridge.failure).__name__,
            cause_type=type(bridge.failure.__cause__).__name__,
            writer_openings=bridge.fence.writer_openings,
            hashes={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in parts.iterdir()
                    if p.is_file() and p.name != '.tikrec-lifecycle.lock'})


def cleanup(owner):
    """Observe exact local retirement and admission refusal after real product cleanup."""
    if protected is not None and (BASE / 'repair-written').exists():
        from tests.test_release_recovery_windows_close import protection
        # Repair only the original test handle, on the original supervisor thread.
        assert protected._same(protected.original)
        protection(protected.original, False)
    result = original_cleanup(owner)
    runtime = owner.runtime
    if runtime is not None:
        fenced = False
        try:
            runtime.start('https://www.tiktok.com/@fixture.late/live', runtime.root / 'late.mp4')
        except RecordingBusy:
            fenced = True
        record('cleanup-return', owner=id(owner), result=owner.last_result,
            authority_retired=authority_retired(runtime), sqlite_owned=runtime.connections.has_ownership(),
            admission_fenced=fenced,
            state_pins=len(owner.state.pins), state_guards=sum(g.retained for g in owner.state.native_close_guards),
            captures=[{'session': sid, 'bridge': id(e['bridge']), 'failure': id(e['bridge'].failure),
                'done': e['done'], 'joined': not e['thread'].is_alive(),
                'lease_closed': e['bridge'].lease.closed,
                'lease_native_retired': not e['bridge'].lease.handle.guard.retained,
                'fence_closed': not e['bridge'].fence.active, 'inflight': e['bridge'].fence.inflight,
                'sources_opened': e['bridge'].fence.sources_opened,
                'sources_closed': e['bridge'].fence.sources_closed,
                'raw_retired': e['bridge'].fence.inputs.retired(),
                'writers_retired': e['bridge'].fence.writers.retired(),
                'writer_openings': e['bridge'].fence.writer_openings}
                for sid, e in runtime.captures.items()],
            threads=[t.name for t in threads() if t is not current_thread()])
    return result


generated.operational_composition.source_options = supplied
service_runtime_capture.run_capture = capture
operational_command.OperationalCommand.cleanup = cleanup
if os.environ.get('TIKREC_WRITTEN_CLOSE_FAULT'):
    from tikrec.capture_writer_owners import CaptureWriterOwners
    original_open = CaptureWriterOwners.open
    def opening(self, path, mode, **options):
        global protected
        stream = original_open(self, path, mode, **options)
        guard = self.streams[-1]['guard']
        if mode == 'xb' and protected is None:
            from tests.test_release_recovery_windows_close import protection
            protected = guard
            protection(guard.original, True)
            record('original-part-protected', guard=id(guard), handle=guard.original)
        return stream
    CaptureWriterOwners.open = opening
if __name__ == '__main__':
    runpy.run_module('tikrec.cli', run_name='__main__')
