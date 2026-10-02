"""Configure independent creator opt-ins for automatic raw-source evidence."""

import argparse
from dataclasses import replace
from typing import TextIO

from .configuration import ConfigurationStore
from .creator_identity import CreatorIdentityError, normalize_creator


def add_raw_copy_command(actions) -> argparse.ArgumentParser:
    """Add explicit enable/disable/list commands beneath the monitor group."""
    raw = actions.add_parser(
        "raw-copy", help="configure per-creator automatic raw-copy",
        description="Automatic raw-copy is off by default; changes apply at service startup.",
    )
    commands = raw.add_subparsers(dest="raw_copy_action", required=True)
    for action in ("enable", "disable"):
        command = commands.add_parser(action, help=f"{action} one creator's automatic raw-copy")
        command.add_argument("creator", metavar="CREATOR")
    commands.add_parser("list", help="list saved automatic raw-copy opt-ins")
    return raw


def run_raw_copy_command(arguments: argparse.Namespace, store: ConfigurationStore,
                         stdout: TextIO) -> int:
    """Atomically change one durable preference without changing monitoring."""
    if arguments.raw_copy_action == "list":
        creators = store.load().automatic_raw_copy_creators
        if not creators:
            print("No automatic raw-copy creators.", file=stdout)
        else:
            for creator in creators:
                print(f"@{creator}", file=stdout)
        return 0
    creator = normalize_creator(arguments.creator)

    def change(current):
        creators = current.automatic_raw_copy_creators
        if arguments.raw_copy_action == "enable":
            if creator in creators:
                raise CreatorIdentityError(f"automatic raw-copy is already enabled: @{creator}")
            return replace(current, automatic_raw_copy_creators=creators + (creator,))
        if creator not in creators:
            raise CreatorIdentityError(f"automatic raw-copy is not enabled: @{creator}")
        # Preferences survive monitor removal; only an explicit disable removes one.
        return replace(current, automatic_raw_copy_creators=tuple(
            item for item in creators if item != creator))

    store.update(change)
    verb = "Enabled" if arguments.raw_copy_action == "enable" else "Disabled"
    print(f"{verb} automatic raw-copy: @{creator}; applies at service startup.", file=stdout)
    return 0
