"""Command-line options and preference resolution for explicit validation."""

from __future__ import annotations

import argparse
from pathlib import Path

from .configuration import ConfigurationStore, default_config_path


def add_validation_command(subcommands) -> argparse.ArgumentParser:
    """Add the standalone validation command and its explicit mode overrides."""
    validate = subcommands.add_parser("validate", help="check recording health")
    validate.add_argument("target", metavar="TARGET")
    validation_mode = validate.add_mutually_exclusive_group()
    validation_mode.add_argument(
        "--deep", dest="validation_mode", action="store_const", const="deep",
        help="fully decode completed output",
    )
    validation_mode.add_argument(
        "--standard", dest="validation_mode", action="store_const", const="standard",
        help="use standard completed-output checks",
    )
    validate.add_argument("--json", action="store_true", help="print structured results")
    return validate


def effective_validation_mode(explicit_mode: str | None, config_path: str | None) -> str:
    """Resolve an explicit mode before lazily consulting per-user configuration."""
    if explicit_mode is not None:
        return explicit_mode
    path = Path(config_path) if config_path else default_config_path()
    return ConfigurationStore(path).load().effective_validation_mode
