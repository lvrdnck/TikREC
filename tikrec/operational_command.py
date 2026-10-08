"""Headless service supervisor; no finite-pilot composition or lifetime budget."""
import time
from pathlib import Path
from types import SimpleNamespace

from .configuration import ConfigurationStore
from .control_cli import read_token
from .operational_composition import compose
from .operational_identity import identity
from .operational_policy import OperatingPolicy
from .operational_reporting import Reporting
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
        self.reporting = Reporting()
        self.last_observation = None
        self.session_observations = {}

    def receipt(self, event, **values):
        """Write sanitized bounded on-disk receipts; console receives lifecycle only."""
        error = self.reporting.write(self.diagnostics, event, **values)
        if error is not None:
            # Save exact failure/attachments before any later report or cleanup can fail.
            if self.primary is None:
                self.primary = error
            self.envelope.failed = True
            if not self.shutdown_requested:
                raise error

    def report_cleanup(self, result, original):
        """Reporting cannot interrupt the inherited recorded cleanup result or control."""
        self.receipt('shutdown', **result,
                     primary_type=None if original is None else type(original).__name__)

    def cleanup(self):
        """Preserve original parent cleanup semantics, then record the actual outcome."""
        if self.runtime is not None and self.runtime.paused not in {None, 'low_free_space', 'storage_unavailable'}:
            self.stop_reason = self.stop_reason or 'unsupported_work_needs_attention'
        return super().cleanup()

    def run(self):
        """Check space without requests, retain uncertain owners for explicit cleanup."""
        while True:
            try:
                command = self.control()
                if (command == 'shutdown' and not self.shutdown_requested
                        or command == 'cleanup' and self.shutdown_requested):
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
                if self.primary is None:
                    self.primary = error
                self.envelope.failed = True
                try:
                    self.receipt('failure', reason='operational_supervision_failed',
                                 primary_type=type(self.primary).__name__)
                except BaseException:
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
    reporting = Reporting()
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
            owner.receipt('initialized', catalog_id=options.catalog_id,
                          schema=10, backend='operational_schema10')
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
        except BaseException:
            pass  # The reporter already retained the exact fault; retirement is confirmed.
        final_code = owner.exit_code() if owner.primary is not None else code
        if final_code != code:
            # A late reporting failure supersedes the prospective exit on surviving sinks.
            # Failed channels stay disabled; no cleanup/action is repeated for diagnostics.
            owner.receipt('failure', reason='operational_reporting_failed',
                          primary_type=type(owner.primary).__name__)
            owner.receipt('exit', exit_code=final_code, complete=owner.last_result['complete'])
        return final_code
    except BaseException as error:
        if owner is not None:
            if owner.primary is None:
                owner.primary = error
            owner.envelope.failed = True
            reporting = owner.reporting
        # Saving the primary above retains its exact attached native/SQLite owners.
        reporting.write(None if owner is None else owner.diagnostics, 'failure',
                        reason='operational_startup_refused',
                        primary_type=type(error if owner is None else owner.primary).__name__)
        if owner is not None:
            if not owner.cleanup():
                return owner.run()
        return 2
