"""Journal-backed capture admission and UUID/generation-bound callbacks."""

from pathlib import Path

from .creator_identity import creator_from_live_url
from .recording import RecordingBusy
from .recording_manager import RecordingDuplicate
from .session_journal_types import JournalConflict, require
from .tiktok_identity import canonical_room_id
from .service_runtime_worker import capture_cleanup_blocked, prune_leases



def retain_thread_after_error(runtime, thread, error):
    """Keep started or unconfirmed threads after a lost startup acknowledgement."""
    if thread is None:
        return False
    if not isinstance(error, Exception):
        # An interruption may occur between native creation and startup reporting.
        return True
    try:
        # Standard Thread.start creation errors precede startup; ident survives exit.
        return thread.ident is not None or thread.is_alive()
    except BaseException as secondary:
        runtime.record_error(secondary)
        return True


def start_capture(runtime, url, output, raw, room, automatic_claim=None):
    """Reserve once before launching real capture; failed launch preserves its unit."""
    creator = creator_from_live_url(url)
    require(type(raw) is bool, 'raw_copy must be a boolean')
    if room is not None:
        room = canonical_room_id(room)
    require(Path(output).is_absolute(), 'output must be absolute')
    reason = runtime.storage_reason()
    if reason:
        raise RecordingBusy(reason)
    with runtime.lock:
        if not runtime.started or runtime.closed:
            raise RecordingBusy('service is not accepting starts')
        if runtime.connections.failed(runtime):
            raise RecordingBusy('catalog_cleanup_needs_attention')
        if capture_cleanup_blocked(runtime, runtime.journal.status()):
            raise RecordingBusy('capture_cleanup_needs_attention')
        try:
            bridge = runtime.authority.reserve(output, creator, room, raw_copy=raw,
                started_at=runtime.clock(), automatic_claim=automatic_claim)
        except JournalConflict as error:
            prune_leases(runtime)
            if 'room' in str(error) or 'creator' in str(error) or 'page' in str(error):
                raise RecordingDuplicate('public LIVE already owned') from error
            if 'limit' in str(error):
                raise RecordingBusy('finalization_backlog_full') from error
            if 'capacity' in str(error):
                raise RecordingBusy('recording capacity is unavailable') from error
            raise
        except BaseException:
            prune_leases(runtime)
            raise
        sid, generation = bridge.intent.session_id, bridge.binding['generation']
        entry = {'bridge': bridge, 'state': 'resolving', 'bytes_written': 0,
                 'current_part': None, 'thread': None, 'done': False}
        runtime.captures[sid] = entry
        runtime.latest[bridge.binding['slot']] = sid
        try:
            thread = runtime.thread_factory(target=run_capture, args=(runtime, sid, generation),
                name='tikrec-isolated-capture-' + sid, daemon=False)
            entry['thread'] = thread
            thread.start()
        except BaseException as error:
            runtime.record_error(error)
            if not retain_thread_after_error(runtime, entry['thread'], error):
                entry['thread'], entry['done'] = None, True
            entry['state'] = 'needs_attention'
            runtime.capture_errors[sid] = error
            # Preserve durable acceptance across known launch failure or lost acknowledgement.
            raise
        return runtime.session_status(sid)


def callback(runtime, sid, generation, kind, *values):
    """Apply only to the exact live binding and original generation."""
    with runtime.lock:
        entry = runtime.captures.get(sid)
        if entry is None or entry['done'] or runtime.closed:
            return False
        bridge = entry['bridge']
        bindings = runtime.journal.status()['bindings']
        if generation != bridge.binding['generation'] or not any(
                b['session'] == sid and b['generation'] == generation for b in bindings):
            return False
        if kind == 'state':
            entry['state'] = values[0]
        elif kind == 'heartbeat':
            entry['current_part'], entry['bytes_written'] = str(values[0]), values[1]
        else:
            raise ValueError('unknown capture callback')
        return True


def run_capture(runtime, sid, generation):
    """Use the accepted bridge through H; notification never authorizes slot reuse."""
    entry = runtime.captures[sid]
    bridge = entry['bridge']
    try:
        options = dict(runtime.observations(bridge))
        # Callbacks close over the accepted identity, never a mutable slot index.
        options['state'] = lambda state: callback(runtime, sid, generation, 'state', state)
        options['heartbeat'] = lambda path, count: callback(runtime, sid, generation, 'heartbeat', path, count)
        def notify(receipt):
            if runtime.notify is not None:
                runtime.notify(receipt)
            runtime.wake.set()
        result = bridge.run(notify=notify, **options)
        with runtime.lock:
            entry['result'] = result
        for error in result.post_h_errors:
            runtime.record_error(error)
        if result.failure is not None:
            runtime.record_error(result.failure)
    except BaseException as error:
        runtime.record_error(error)
        with runtime.lock:
            runtime.capture_errors[sid] = error
            entry['state'] = 'needs_attention'
    finally:
        runtime.connections.cleanup(runtime)
        with runtime.lock:
            entry['done'] = True
        # Worker reconciles even if this hint is absent; keep entry until thread exit.
        runtime.wake.set()
