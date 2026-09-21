"""CLI debug flags and lazy unexpected-error traceback selection."""

from __future__ import annotations

import argparse
import sys
import traceback
from collections.abc import Sequence
from pathlib import Path
from typing import TextIO

from .configuration import ConfigurationError, ConfigurationStore, default_config_path


def add_debug_arguments(
    parser: argparse.ArgumentParser, *, suppress_default: bool = False
) -> None:
    """Add mutually exclusive debug overrides before or after a subcommand."""
    default = argparse.SUPPRESS if suppress_default else None
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--debug", dest="debug_tracebacks", action="store_const", const=True,
        default=default, help="print unexpected-error tracebacks",
    )
    group.add_argument(
        "--no-debug", dest="debug_tracebacks", action="store_const", const=False,
        default=default, help="suppress unexpected-error tracebacks",
    )


def parse_arguments(
    parser: argparse.ArgumentParser, argv: Sequence[str] | None
) -> argparse.Namespace:
    """Parse CLI arguments while rejecting conflicting cross-parser debug flags."""
    values = list(sys.argv[1:] if argv is None else argv)
    if "--debug" in values and "--no-debug" in values:
        parser.error("argument --debug/--no-debug: not allowed together")
    return parser.parse_args(values)


def effective_debug_tracebacks(explicit: bool | None, config_path: str | None) -> bool:
    """Resolve an explicit debug choice before lazily consulting configuration."""
    if explicit is not None:
        return explicit
    path = Path(config_path) if config_path else default_config_path()
    return ConfigurationStore(path).load().effective_debug_tracebacks


def print_unexpected_traceback(
    explicit: bool | None, config_path: str | None, stderr: TextIO
) -> None:
    """Print a selected traceback or explain why its configured default is unusable."""
    try:
        enabled = effective_debug_tracebacks(explicit, config_path)
    except ConfigurationError as error:
        detail = " ".join(str(error).split())
        print(f"tikrec: debug traceback setting unavailable: {detail}", file=stderr)
        return
    if enabled:
        traceback.print_exc(file=stderr)
