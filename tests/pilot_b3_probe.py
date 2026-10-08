"""Observe retained exact owners around the existing offline pilot command seam."""
import json
import runpy
from threading import get_ident

from tests import pilot_command_probe as fixture
from tikrec.pilot_command import PilotCommand

original = PilotCommand.cleanup


def observed_cleanup(owner):
    """Record owner reachability without changing product cleanup or accounting."""
    result = original(owner)
    runtime = owner.runtime
    if runtime is not None:
        captures = {}
        for sid, entry in runtime.captures.items():
            bridge, worker = entry['bridge'], entry['thread']
            captures[sid] = {'done': entry['done'],
                'thread_alive': None if worker is None else worker.is_alive(),
                'fence_active': bridge.fence.active,
                'fence_errors': len(bridge.fence.cleanup_errors),
                'lease_closed': bridge.lease.closed,
                'handle_closed': bridge.lease.handle.closed,
                'authority_bridge': runtime.authority.bridges.get(sid) is bridge,
                'authority_lease': bridge.lease in runtime.authority.leases}
        document = {'complete': result, 'thread': get_ident(), 'captures': captures,
            'connections_owned': runtime.connections.has_ownership(),
            'worker_alive': runtime.worker is not None and runtime.worker.is_alive(),
            'requests_owned': len(owner.server.requests.owners),
            'listener_fd': owner.server.socket.fileno(),
            'authority_closed': runtime.authority_closed}
        with (fixture.BASE / 'owner-observations.jsonl').open('a') as stream:
            stream.write(json.dumps(document) + '\n')
    return result


PilotCommand.cleanup = observed_cleanup
if __name__ == '__main__':
    runpy.run_module('tikrec.pilot', run_name='__main__')
