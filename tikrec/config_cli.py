"""Command-line surface for inspecting and changing per-user configuration."""

from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path
from typing import TextIO

from .configuration import (
    ConfigurationStore,
    configured_output_directory,
    default_config_path,
)


def add_config_command(subcommands) -> argparse.ArgumentParser:
    """Add the small owner-facing configuration command group."""
    config = subcommands.add_parser("config", help="inspect or change per-user defaults")
    actions = config.add_subparsers(dest="config_action", required=True)
    show = actions.add_parser("show", help="show configured and effective defaults")
    show.add_argument("--json", action="store_true", help="print structured results")
    actions.add_parser("path", help="print the configuration file path")
    set_command = actions.add_parser("set", help="set one persisted default")
    set_command.add_argument("setting", choices=["output-directory"])
    set_command.add_argument("value", metavar="DIRECTORY")
    unset = actions.add_parser("unset", help="remove one persisted default")
    unset.add_argument("setting", choices=["output-directory"])
    return config


def run_config_command(arguments: argparse.Namespace, stdout: TextIO) -> int:
    """Run one configuration action and print an owner-readable result."""
    path = Path(arguments.config_path) if arguments.config_path else default_config_path()
    store = ConfigurationStore(path)
    if arguments.config_action == "path":
        print(path, file=stdout)
        return 0
    configuration = store.load()
    if arguments.config_action == "show":
        source = "configuration" if configuration.output_directory is not None else "current_working_directory"
        effective = configuration.output_directory or Path.cwd()
        result = {
            "config_path": str(path),
            "exists": path.is_file(),
            "output_directory": (
                str(configuration.output_directory)
                if configuration.output_directory is not None else None
            ),
            "effective_output_directory": str(effective),
            "output_directory_source": source,
        }
        if arguments.json:
            print(json.dumps(result, indent=2, sort_keys=True), file=stdout)
        else:
            print(f"Config path: {result['config_path']}", file=stdout)
            print(f"Config file exists: {'yes' if result['exists'] else 'no'}", file=stdout)
            print(f"Configured output directory: {result['output_directory'] or '(not set)'}", file=stdout)
            print(f"Effective output directory: {result['effective_output_directory']}", file=stdout)
            print(f"Source: {source}", file=stdout)
        return 0
    if arguments.config_action == "set":
        directory = configured_output_directory(arguments.value)
        store.save(replace(configuration, output_directory=directory))
        print(f"Set output directory: {directory}", file=stdout)
        return 0
    store.save(replace(configuration, output_directory=None))
    print("Unset output directory", file=stdout)
    return 0
