"""Resolve the persisted and command-line LIVE recovery-window policy."""

import argparse
from pathlib import Path

from .configuration import (
    ConfigurationError,
    ConfigurationStore,
    configured_recovery_window_seconds,
    default_config_path,
    validate_recovery_window_seconds,
)
from .retry_policy import RetryPolicy


def recovery_window_argument(value: str) -> int:
    """Parse one strict integer command-line recovery-window override."""
    try:
        return configured_recovery_window_seconds(value)
    except ConfigurationError as error:
        raise argparse.ArgumentTypeError(str(error)) from None


def effective_retry_policy(override: int | None, config_path: str | None) -> RetryPolicy:
    """Apply CLI, configuration, and built-in precedence without needless I/O."""
    if override is not None:
        return RetryPolicy(window_seconds=validate_recovery_window_seconds(override))
    path = Path(config_path) if config_path else default_config_path()
    configuration = ConfigurationStore(path).load()
    return RetryPolicy(window_seconds=configuration.effective_recovery_window_seconds)
