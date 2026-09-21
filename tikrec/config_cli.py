"""Command-line surface for inspecting and changing per-user configuration."""

from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path
from typing import TextIO

from .configuration import (
    ConfigurationStore,
    configured_debug_tracebacks,
    configured_recovery_window_seconds,
    configured_output_directory,
    configured_validation_mode,
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
    settings = [
        "output-directory", "recovery-window-seconds", "validation-mode",
        "debug-tracebacks",
    ]
    set_command.add_argument("setting", choices=settings)
    set_command.add_argument("value", metavar="VALUE")
    unset = actions.add_parser("unset", help="remove one persisted default")
    unset.add_argument("setting", choices=settings)
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
            "recovery_window_seconds": configuration.recovery_window_seconds,
            "effective_recovery_window_seconds": (
                configuration.effective_recovery_window_seconds
            ),
            "recovery_window_source": (
                "configuration"
                if configuration.recovery_window_seconds is not None
                else "built_in_default"
            ),
            "validation_mode": configuration.validation_mode,
            "effective_validation_mode": configuration.effective_validation_mode,
            "validation_mode_source": (
                "configuration"
                if configuration.validation_mode is not None
                else "built_in_default"
            ),
            "debug_tracebacks": configuration.debug_tracebacks,
            "effective_debug_tracebacks": configuration.effective_debug_tracebacks,
            "debug_tracebacks_source": (
                "configuration"
                if configuration.debug_tracebacks is not None
                else "built_in_default"
            ),
        }
        if arguments.json:
            print(json.dumps(result, indent=2, sort_keys=True), file=stdout)
        else:
            print(f"Config path: {result['config_path']}", file=stdout)
            print(f"Config file exists: {'yes' if result['exists'] else 'no'}", file=stdout)
            print(f"Configured output directory: {result['output_directory'] or '(not set)'}", file=stdout)
            print(f"Effective output directory: {result['effective_output_directory']}", file=stdout)
            print(f"Source: {source}", file=stdout)
            print(
                "Configured recovery window: "
                f"{result['recovery_window_seconds'] or '(not set)'}",
                file=stdout,
            )
            print(
                f"Effective recovery window: {result['effective_recovery_window_seconds']} seconds",
                file=stdout,
            )
            print(f"Recovery window source: {result['recovery_window_source']}", file=stdout)
            print(
                f"Configured validation mode: {result['validation_mode'] or '(not set)'}",
                file=stdout,
            )
            print(
                f"Effective validation mode: {result['effective_validation_mode']}",
                file=stdout,
            )
            print(f"Validation mode source: {result['validation_mode_source']}", file=stdout)
            configured_debug = result["debug_tracebacks"]
            configured_debug_text = (
                "(not set)" if configured_debug is None else str(configured_debug).lower()
            )
            print(f"Configured debug tracebacks: {configured_debug_text}", file=stdout)
            print(
                "Effective debug tracebacks: "
                f"{str(result['effective_debug_tracebacks']).lower()}",
                file=stdout,
            )
            print(f"Debug tracebacks source: {result['debug_tracebacks_source']}", file=stdout)
        return 0
    if arguments.config_action == "set":
        if arguments.setting == "output-directory":
            value = configured_output_directory(arguments.value)
            store.save(replace(configuration, output_directory=value))
            print(f"Set output directory: {value}", file=stdout)
        elif arguments.setting == "recovery-window-seconds":
            value = configured_recovery_window_seconds(arguments.value)
            store.save(replace(configuration, recovery_window_seconds=value))
            print(f"Set recovery window: {value} seconds", file=stdout)
        elif arguments.setting == "validation-mode":
            value = configured_validation_mode(arguments.value)
            store.save(replace(configuration, validation_mode=value))
            print(f"Set validation mode: {value}", file=stdout)
        else:
            value = configured_debug_tracebacks(arguments.value)
            store.save(replace(configuration, debug_tracebacks=value))
            print(f"Set debug tracebacks: {str(value).lower()}", file=stdout)
        return 0
    if arguments.setting == "output-directory":
        store.save(replace(configuration, output_directory=None))
        print("Unset output directory", file=stdout)
    elif arguments.setting == "recovery-window-seconds":
        store.save(replace(configuration, recovery_window_seconds=None))
        print("Unset recovery window", file=stdout)
    elif arguments.setting == "validation-mode":
        store.save(replace(configuration, validation_mode=None))
        print("Unset validation mode", file=stdout)
    else:
        store.save(replace(configuration, debug_tracebacks=None))
        print("Unset debug tracebacks", file=stdout)
    return 0
