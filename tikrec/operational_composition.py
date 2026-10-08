"""Normal service opt-in composition, sharing one accepted runtime and HTTP owner."""
from .admission import RecordingAdmission
from .automation import AutomationCoordinator
from .configuration import ConfigurationStore
from .monitoring import CreatorMonitor
from .operational_source import source_options
from .service_http_runtime import IsolatedRecordingHTTPServer
from .service_runtime import IsolatedServiceRuntime
from .session_journal_types import require
from .operational_diagnostics import Diagnostics
from .pilot_identity import local


def compose(owner, options, token, configuration, retry_policy):
    """Enable existing automation only after the HTTP listener binds successfully."""
    policy, state = owner.envelope, owner.state
    storage = policy.storage('media')
    owner.runtime = IsolatedServiceRuntime(state.journal, state.home / 'media',
        ffmpeg=options.ffmpeg, ffprobe=options.ffprobe, storage_status=storage,
        catalog_storage=policy.storage('state'), resource_policy=policy,
        observations=lambda bridge: source_options(policy, bridge, options.ffprobe, retry_policy),
        settlement_options={'writer_budget': policy.writer_budget}, authority_cleanup_guards=True)
    # Acquire sole catalog authority before touching logs; persist launch before work.
    owner.diagnostics = Diagnostics(state.home / 'logs')
    owner.receipt('startup', **owner.startup)
    admission = RecordingAdmission(owner.runtime.root, owner.runtime.health, storage_status=storage)
    automation = AutomationCoordinator(owner.runtime, admission, state.automation,
        automatic_raw_copy_creators=configuration.automatic_raw_copy_creators)
    def creator_loader():
        # Atomic reload may legitimately replace config bytes; only creators are adopted.
        require(local(options.config_path).stat().st_size <= 1024**2, 'configuration exceeds bound')
        return ConfigurationStore(options.config_path).load(missing_ok=False).monitored_creators
    monitor = CreatorMonitor(configuration.monitored_creators,
        cycle_completed=automation.cycle_completed, creator_loader=creator_loader)
    try:
        owner.server = IsolatedRecordingHTTPServer(options.host, options.port,
            runtime=owner.runtime, admission=admission, automation=automation, monitor=monitor, token=token)
    except BaseException as error:
        owner.server = getattr(error, 'isolated_server', None)
        raise
    owner.server.timeout = 0.1
