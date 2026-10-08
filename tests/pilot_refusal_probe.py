"""Observe unchanged originals/native owners around real pilot refusal shutdown."""

import hashlib
import json
import os
import runpy

from tests import pilot_command_probe as fixture
from tests.test_release_recovery_windows_close import protection
from tikrec.capture_handoff_authority import CaptureAuthority
from tikrec.capture_input_owners import CaptureInputOwners
from tikrec.pilot_command import PilotCommand
from tikrec import service_runtime_capture

blocked = []
reserve, open_raw = CaptureAuthority.reserve, CaptureInputOwners.open
cleanup = PilotCommand.cleanup
run_capture = service_runtime_capture.run_capture


def observed_capture(runtime, sid, generation):
    """Expose completed product unwinding before test hashes race its exclusive inventory."""
    run_capture(runtime, sid, generation)
    (fixture.BASE / (sid + '-capture-retired')).write_text('original capture function returned')


def fixture_reserve(owner, *args, **kwargs):
    """Protect only the exact original lease, never a path or later descriptor occupant."""
    bridge = reserve(owner, *args, **kwargs)
    if fixture.MODE == 'refusal-lease-close':
        guard = bridge.lease.handle.guard
        protection(guard.original, True)
        blocked.append(guard)
    return bridge


def fixture_open(owner, path, mode, **options):
    """Inject native protection on one generated raw or arrival writer before ingress."""
    stream = open_raw(owner, path, mode, **options)
    wanted = '.raw' if fixture.MODE == 'refusal-raw-close' else '.jsonl'
    if fixture.MODE in {'refusal-raw-close', 'refusal-arrival-close'} and path.suffix == wanted and not blocked:
        protection(stream.guard.original, True)
        blocked.append(stream.guard)
    return stream


def media_hashes(root):
    """Read only generated original evidence; lock content is mutable lifecycle metadata."""
    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*')
            if p.is_file() and p.name != '.tikrec-lifecycle.lock'}


def snapshot(owner):
    """Record original references and native proof without replacing cleanup behavior."""
    runtime = owner.runtime
    if runtime is None:
        return None
    captures = {}
    for sid, entry in runtime.captures.items():
        bridge, fence = entry['bridge'], entry['bridge'].fence
        captures[sid] = {'done': entry['done'], 'thread_alive': entry['thread'].is_alive(),
            'fence_active': fence.active, 'inflight': fence.inflight,
            'source_counts': [fence.sources_opened, fence.sources_closed],
            'writer_openings': fence.writer_openings, 'fence_errors': len(fence.cleanup_errors),
            'raw_errors': len(fence.inputs.errors),
            'raw_guards': [g.retained for g in fence.inputs.native_close_guards],
            'raw_closed': [s['raw'].closed for s in fence.inputs.streams],
            'lease_closed': bridge.lease.closed, 'handle_closed': bridge.lease.handle.closed,
            'lease_native_retained': bridge.lease.handle.guard.retained,
            'lease_errors': len(bridge.lease.cleanup_errors),
            'authority_bridge': runtime.authority.bridges.get(sid) is bridge,
            'authority_lease': bridge.lease in runtime.authority.leases,
            'refusal_retired': entry.get('refusal_retired')}
    durable = None if runtime.connections.closing and runtime.connections.enabled else {'status': runtime.journal.status(),
        'sessions': {sid: runtime.journal.session(sid) for sid in captures}}
    return {'pid': os.getpid(), 'captures': captures, 'media': media_hashes(runtime.root), 'durable': durable,
        'connections_owned': runtime.connections.has_ownership(),
        'worker_alive': runtime.worker.is_alive(),
        'requests_owned': len(owner.server.requests.owners), 'listener_fd': owner.server.socket.fileno(),
        'authority_closed': runtime.authority_closed,
        'authority_native_retained': [g.retained for g in runtime.authority.native_close_guards]}


def observed_cleanup(owner):
    """Remove only named generated faults on repair, then call actual product cleanup once."""
    if (fixture.BASE / 'repair').exists():
        for guard in blocked:
            if guard.original is not None and guard._same(guard.original):
                protection(guard.original, False)
    before = snapshot(owner)
    result = cleanup(owner)
    after = snapshot(owner)
    with (fixture.BASE / 'refusal-owners.jsonl').open('a') as stream:
        stream.write(json.dumps({'before': before, 'after': after, 'complete': result}) + '\n')
    return result


CaptureAuthority.reserve, CaptureInputOwners.open = fixture_reserve, fixture_open
PilotCommand.cleanup = observed_cleanup
service_runtime_capture.run_capture = observed_capture
if __name__ == '__main__':
    runpy.run_module('tikrec.pilot', run_name='__main__')
