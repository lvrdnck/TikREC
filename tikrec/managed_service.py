"""Startup wiring for the protected existing two-slot service."""

from pathlib import Path

from .managed_paths import ProtectedPath
from .managed_registry import installed
from .managed_storage import ManagedStorage
from .retry_policy import RetryPolicy
from .service_configuration import load_service_configuration


def run_managed_service(arguments, token, service_runner) -> None:
    """Start the existing service only from protected code/configuration/storage."""
    if arguments.config_path is not None or arguments.recovery_window_seconds is not None:
        raise ValueError("managed service uses only its protected authoritative configuration")
    if arguments.token_file is None or token is None:
        raise ValueError("managed service requires a protected bearer token file")
    authority = ManagedStorage(Path(arguments.managed_storage))
    try:
        token_path = ProtectedPath(Path(arguments.token_file), 0, directory=False)
        token_path.close()
        with installed(authority):
            configuration = load_service_configuration(authority.config_path, validate_all=True)
            if configuration.output_directory != authority.root:
                raise ValueError("managed configuration must select its exact recording root")
            service_runner(host=arguments.host, port=arguments.port, token=token,
                           retry_policy=RetryPolicy(window_seconds=configuration.recovery_window_seconds),
                           monitored_creators=configuration.monitored_creators,
                           output_directory=authority.root,
                           minimum_free_space_gib=configuration.minimum_free_space_gib)
    finally:
        authority.close()
