"""Foreground accept/supervision loop; incomplete cleanup stays reachable in-process."""
import json
import time
from pathlib import Path

from .pilot_composition import compose
from .pilot_identity import local
from .pilot_state import PilotState
from .session_journal_types import identifier, require


def emit(event, **values):
    """Print bounded nonsecret receipts; never dump exception text or command secrets."""
    print(json.dumps({'event': event, **values}, allow_nan=False), flush=True)


class PilotCommand:
    """Own launcher pins, server, runtime, original failures and explicit cleanup retries."""

    def __init__(self, options, envelope):
        self.options, self.envelope = options, envelope
        self.state = PilotState(Path(options.home))
        self.runtime = self.server = self.primary = None
        self.shutdown_requested, self.last_control = False, None
        self.next_observation = 0
        self.last_result = None
        self.stop_reason = None

    def exit_code(self):
        """Keep an unsupported/safety stop nonzero even after explicit cleanup succeeds."""
        # Manual shutdown may beat the observation tick; the original refusal remains a failure.
        refused = self.runtime is not None and any(
            e.get('refusal_retired') for e in self.runtime.captures.values())
        return 2 if self.primary is not None else 3 if self.stop_reason is not None or refused else 0

    def start(self, source, token):
        """Initialize/reopen explicitly, then bind/start the existing complete composition."""
        try:
            self.state.open(self.options.mode, self.options.catalog_id, source)
            self.envelope.launch_ready()
            require(self.envelope.inspect() is None, 'existing pilot data exceeds operating envelope')
            # Reopening never replays a previous run's shutdown/cleanup operation.
            self.control()
            compose(self, self.options, token)
        except BaseException as error:
            self.primary = error
            raise
        emit('ready', **source, catalog_id=self.state.journal.catalog_id,
             catalog=str(self.state.journal.path), media=str(self.runtime.root),
             automation=str(self.state.automation.path), port=self.server.server_port,
             control=str(self.state.home / 'control.json'), schema=10,
             capacities={'captures': 2, 'finalizers': 1, 'units': 8, 'lifetime_sessions': 8})

    def control(self):
        """Consume a bounded explicit local operation; same nonce cannot repeat cleanup."""
        path = self.state.home / 'control.json'
        if not path.exists():
            return None
        local(path)
        require(path.stat().st_size <= 512, 'pilot control exceeds bound')
        # A writer may still be replacing/truncating a control file; retry observation,
        # never invent a shutdown/cleanup request from partial bytes.
        try:
            value = json.loads(path.read_text(encoding='utf-8-sig'))
        except (ValueError, OSError):
            return None
        require(isinstance(value, dict) and set(value) == {'operation', 'command'}, 'invalid pilot control')
        identifier(value['operation'])
        require(value['command'] in {'shutdown', 'cleanup'}, 'invalid pilot control command')
        if value['operation'] == self.last_control:
            return None
        self.last_control = value['operation']
        return value['command']

    def cleanup(self):
        """Use original-owner APIs on the launching thread; never close stale numbers."""
        self.shutdown_requested = True
        result = {'complete': True}
        try:
            if self.server is not None:
                result = self.server.server_close()
            elif self.runtime is not None:
                result = self.runtime.shutdown()
        except BaseException as error:
            if self.primary is None:
                self.primary = error
            result = {'complete': False, 'reason': 'pilot_cleanup_unconfirmed'}
        # Setup errors may retain exact native/SQLite owners before server construction.
        original = self.primary
        owners = [*getattr(original, 'capture_native_owners', ())]
        partial = getattr(original, 'scratch_native_owner', None)
        if partial is not None:
            owners.append(partial)
        for held in owners:
            try:
                held.close()
            except BaseException:
                result = {**result, 'complete': False}
        authority = getattr(original, 'capture_authority_owner', None)
        if authority is not None:
            # ExitStack already consumed callbacks, but exact guarded owners survive.
            for guard in authority.native_close_guards:
                try:
                    guard.close_retired_reference()
                    guard.close()
                except BaseException:
                    result = {**result, 'complete': False}
            if any(g.retained for g in authority.native_close_guards):
                result = {**result, 'complete': False}
        reader = getattr(original, 'manifest_fence_owner', None)
        if reader is not None:
            try:
                if reader.cleanup():
                    result = {**result, 'complete': False}
            except BaseException:
                result = {**result, 'complete': False}
        if result.get('complete'):
            result = {**result, 'complete': self.state.close()}
        self.last_result = result
        self.report_cleanup(result, original)
        return result.get('complete') is True

    def report_cleanup(self, result, original):
        """Emit the recorded result; operational callers can isolate their failed sinks."""
        emit('shutdown', **result, primary_type=None if original is None else type(original).__name__)

    def run(self):
        """Supervise actual acceptance until confirmed stop; retries require explicit control."""
        while True:
            try:
                command = self.control()
                if command == 'shutdown' or command == 'cleanup' and self.shutdown_requested:
                    if self.cleanup():
                        return self.exit_code()
                if not self.shutdown_requested:
                    if self.envelope.clock() >= self.next_observation:
                        self.next_observation = self.envelope.clock() + 1
                        reason = self.envelope.inspect()
                        unsupported = any(self.runtime.session_status(u['session'])['needs_attention']
                                          for u in self.runtime.journal.status()['units'])
                        if unsupported or self.runtime.paused and self.runtime.paused not in {'low_free_space'}:
                            reason = 'pilot_unsupported_or_uncertain_state'
                        emit('observation', **self.envelope.observed,
                             finalization=self.runtime.health()['finalization'])
                        if reason:
                            self.stop_reason = reason
                            emit('stop_condition', reason=reason)
                            if self.cleanup():
                                return 3
                    if not self.shutdown_requested:
                        self.server.handle_request()
                else:
                    time.sleep(0.1)
            except KeyboardInterrupt:
                if self.cleanup():
                    return self.exit_code()
            except BaseException as error:
                if self.primary is None:
                    self.primary = error
                emit('failure', reason='pilot_supervision_failed', primary_type=type(self.primary).__name__)
                if self.cleanup():
                    return 2
                # Keep the same original owners; no implicit cleanup retry on each poll.
                while True:
                    try:
                        if self.control() == 'cleanup' and self.cleanup():
                            return 2
                        time.sleep(0.1)
                    except BaseException:
                        emit('shutdown', complete=False, reason='explicit_cleanup_required')
                        time.sleep(0.1)
