"""Headless service supervisor; no finite-pilot composition or lifetime budget."""
import json
import time
from pathlib import Path
from types import SimpleNamespace

from .configuration import ConfigurationStore
from .control_cli import read_token
from .operational_composition import compose
from .operational_identity import identity
from .operational_policy import OperatingPolicy
from .operational_state import ServiceState
from .pilot_command import PilotCommand
from .pilot_identity import local
from .retry_policy import RetryPolicy
from .service_bind import validate_bind
from .session_journal_types import require


class OperationalCommand(PilotCommand):
    """Share only exact-owner cleanup/local nonce control with the accepted launcher."""

    def __init__(self, options, policy):
        super().__init__(options, policy)
        self.state = ServiceState(options.home)
        self.diagnostics = None
        self.last_observation = None
        self.session_observations = {}

    def receipt(self, event, **values):
        """Write sanitized bounded on-disk receipts; console receives lifecycle only."""
        if self.diagnostics is not None:
            self.diagnostics.emit(event, **values)
        if event not in {'observation', 'stop'}:
            print(json.dumps({'event': event, **values}, allow_nan=False), flush=True)

    def cleanup(self):
        """Preserve original parent cleanup semantics, then record the actual outcome."""
        if self.runtime is not None and self.runtime.paused not in {None, 'low_free_space', 'storage_unavailable'}:
            self.stop_reason = self.stop_reason or 'unsupported_work_needs_attention'
        complete = super().cleanup()
        try:
            self.receipt('shutdown', **self.last_result)
        except Exception:
            # Sink failure never changes owned release proof or triggers another stop/start.
            self.stop_reason = self.stop_reason or 'diagnostic_sink_unavailable'
        return complete

    def run(self):
        """Check space without requests, retain uncertain owners for explicit cleanup."""
        while True:
            try:
                command = self.control()
                if command == 'shutdown' or command == 'cleanup' and self.shutdown_requested:
                    if self.cleanup():
                        return self.exit_code()
                if self.shutdown_requested:
                    time.sleep(0.1)
                    continue
                # No registry scans/hashes: this loop remains independent of finalizer work.
                self.envelope.supervise(self.runtime)
                if time.monotonic() >= self.next_observation:
                    self.next_observation = time.monotonic() + 1
                    health = self.runtime.health()['finalization']
                    current = {'free_bytes': dict(self.envelope.last),
                               'paused_reason': health['paused_reason'],
                               'outstanding_units': health['outstanding_units']}
                    if current != self.last_observation:
                        self.receipt('observation', **current)
                        self.last_observation = current
                    # Two slot snapshots plus eight outstanding units bound this registry.
                    with self.runtime.lock:
                        ids = {u['session'] for u in self.runtime.journal.status()['units']}
                        ids.update(self.runtime.latest.values())
                    observed = {}
                    for sid in ids:
                        value = self.runtime.session_status(sid)
                        phase = (value['capture_state'], value['finalization_state'], value['stop_requested'])
                        observed[sid] = phase
                        if self.session_observations.get(sid) != phase:
                            self.receipt('stop' if phase[2] else 'observation', session_id=sid,
                                         phase=list(phase), interrupted=value['interrupted'])
                    self.session_observations = observed
                self.server.handle_request()
            except KeyboardInterrupt:
                if self.cleanup():
                    return self.exit_code()
            except BaseException as error:
                self.primary = self.primary or error
                self.envelope.failed = True
                try:
                    self.receipt('failure', reason='operational_supervision_failed',
                                 primary_type=type(self.primary).__name__)
                except Exception:
                    pass
                if self.cleanup():
                    return 2
                # Original owners remain in this supervisor. No automatic cleanup retry.
                while True:
                    try:
                        if self.control() == 'cleanup' and self.cleanup():
                            return 2
                    except BaseException:
                        pass
                    time.sleep(0.1)


def run_operational(arguments):
    """Initialize separately or reopen one explicit home through normal serve CLI."""
    owner = None
    try:
        require(arguments.config_path and arguments.token_file and arguments.journal_catalog_id
                and arguments.ffmpeg and arguments.ffprobe, 'journal mode requires explicit config/token/tools/catalog')
        options = SimpleNamespace(home=Path(arguments.journal_home),
            catalog_id=arguments.journal_catalog_id, mode='init' if arguments.journal_init else 'reopen',
            config_path=Path(arguments.config_path), ffmpeg=Path(arguments.ffmpeg), ffprobe=Path(arguments.ffprobe),
            host=arguments.host, port=arguments.port)
        token_path = local(Path(arguments.token_file))
        require(token_path.stat().st_size <= 1024, 'token file exceeds bound')
        token = read_token(str(token_path))
        options.host = validate_bind(options.host, token)
        require(0 <= options.port <= 65535, 'invalid service port')
        source, config_identity, tools = identity(options.config_path, options.ffmpeg, options.ffprobe)
        configuration = ConfigurationStore(options.config_path).load(missing_ok=False)
        require(configuration.output_directory == options.home / 'media',
                'journal configuration output must equal dedicated home/media')
        require(configuration.retention_max_age_days is None,
                'retention is unsupported for operational journal media')
        retry = RetryPolicy(window_seconds=arguments.recovery_window_seconds or
                            configuration.effective_recovery_window_seconds)
        policy = OperatingPolicy(options.home, configuration.effective_minimum_free_space_gib)
        owner = OperationalCommand(options, policy)
        owner.state.open(options.mode, options.catalog_id, source)
        require(policy.reason('admission') is None, 'operational startup storage unavailable')
        if options.mode == 'init':
            require(owner.state.close(), 'operational initialization cleanup incomplete')
            print(json.dumps({'event': 'initialized', 'catalog_id': options.catalog_id,
                              'schema': 10, 'backend': 'operational_schema10'}), flush=True)
            return 0
        # Consume old control without replay before any callbacks become possible.
        owner.control()
        owner.startup = dict(backend='operational_schema10', source=source,
                            configuration=config_identity, tools=tools, catalog_id=options.catalog_id, schema=10)
        compose(owner, options, token, configuration, retry)
        owner.receipt('ready', port=owner.server.server_port, catalog_id=options.catalog_id,
                      schema=10, control=str(options.home / 'control.json'),
                      capacities={'captures': 2, 'finalizers': 1, 'outstanding_units': 8})
        code = owner.run()
        try:
            owner.receipt('exit', exit_code=code, complete=owner.last_result['complete'])
        except Exception:
            code = 3
        return code
    except BaseException as error:
        print(json.dumps({'event': 'failure', 'reason': 'operational_startup_refused',
                          'primary_type': type(error).__name__}), flush=True)
        if owner is not None:
            owner.primary = owner.primary or error
            if not owner.cleanup():
                return owner.run()
        return 2
