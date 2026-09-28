"""Owner-facing CLI for configuring public creators observed by the service."""

from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path
from typing import TextIO

from .configuration import ConfigurationStore, default_config_path
from .creator_identity import CreatorIdentityError, normalize_creator


def add_monitor_command(subcommands) -> argparse.ArgumentParser:
    """Add creator configuration commands without adding monitoring behavior."""
    monitor = subcommands.add_parser(
        "monitor", help="configure public creators for service monitoring",
        description=(
            "Configure creators observed after the TikREC service restarts; "
            "this command does not contact TikTok or start recording."
        ),
    )
    actions = monitor.add_subparsers(dest="monitor_action", required=True)
    add = actions.add_parser("add", help="add one monitored creator")
    add.add_argument("creator", metavar="CREATOR")
    remove = actions.add_parser("remove", help="remove one monitored creator")
    remove.add_argument("creator", metavar="CREATOR")
    actions.add_parser("list", help="list configured monitored creators")
    return monitor


def run_monitor_command(arguments: argparse.Namespace, stdout: TextIO) -> int:
    """List or atomically update the ordered monitored-creator configuration."""
    path = Path(arguments.config_path) if arguments.config_path else default_config_path()
    store = ConfigurationStore(path)
    configuration = store.load()
    if arguments.monitor_action == "list":
        if not configuration.monitored_creators:
            print("No monitored creators.", file=stdout)
        else:
            for creator in configuration.monitored_creators:
                print(f"@{creator}", file=stdout)
        return 0

    creator = normalize_creator(arguments.creator)
    def change(current):
        monitored = current.monitored_creators
        if arguments.monitor_action == "add":
            if creator in monitored:
                raise CreatorIdentityError(f"creator is already monitored: @{creator}")
            return replace(current, monitored_creators=monitored + (creator,))
        if creator not in monitored:
            raise CreatorIdentityError(f"creator is not monitored: @{creator}")
        return replace(current, monitored_creators=tuple(
            item for item in monitored if item != creator))
    # Monitoring changes must preserve protection committed by another command.
    store.update(change)
    print(f"{'Added' if arguments.monitor_action == 'add' else 'Removed'} monitored "
          f"creator: @{creator}", file=stdout)
    return 0
