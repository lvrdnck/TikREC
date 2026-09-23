"""Owner-facing read-only retention plan and protected-creator settings."""

from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path
from typing import TextIO

from .configuration import ConfigurationStore, default_config_path
from .creator_identity import CreatorIdentityError, normalize_creator
from .retention_plan import plan_retention


def add_retention_command(subcommands) -> argparse.ArgumentParser:
    """Add protection and planning without exposing any cleanup operation."""
    retention = subcommands.add_parser("retention", help="protect creators and preview age retention")
    actions = retention.add_subparsers(dest="retention_action", required=True)
    for action, description in (("protect", "protect one creator from retention"),
                                ("unprotect", "remove explicit protection")):
        command = actions.add_parser(action, help=description)
        command.add_argument("creator", metavar="CREATOR")
    actions.add_parser("protected", help="list explicitly protected creators")
    plan = actions.add_parser("plan", help="read-only preview of immediate sessions")
    plan.add_argument("root", nargs="?", metavar="ROOT")
    plan.add_argument("--json", action="store_true", help="print structured results")
    return retention


def run_retention_command(arguments: argparse.Namespace, stdout: TextIO) -> int:
    """Inspect or atomically update only retention configuration."""
    path = Path(arguments.config_path) if arguments.config_path else default_config_path()
    store = ConfigurationStore(path)
    config = store.load()
    action = arguments.retention_action
    if action == "protected":
        if not config.retention_protected_creators:
            print("No protected creators.", file=stdout)
        else:
            for creator in config.retention_protected_creators:
                print(f"@{creator}", file=stdout)
        return 0
    if action == "plan":
        root = Path(arguments.root) if arguments.root is not None else config.output_directory
        if root is None:
            raise ValueError("retention plan requires ROOT or configured output_directory")
        result = plan_retention(root, config)
        if arguments.json:
            print(json.dumps(result, indent=2, sort_keys=True), file=stdout)
        else:
            age = result["retention_max_age_days"]
            print(f"Retention age: {age if age is not None else 'disabled'}", file=stdout)
            for item in result["sessions"]:
                print(f"{item['parts_directory']}: {item['classification']} "
                      f"({item['reason']}); creator={item['creator'] or 'unknown'}", file=stdout)
            if not result["sessions"]:
                print("No immediate TikREC sessions found.", file=stdout)
        return 0
    creator = normalize_creator(arguments.creator)
    protected = config.retention_protected_creators
    if action == "protect":
        if creator in protected:
            raise CreatorIdentityError(f"creator is already protected: @{creator}")
        store.save(replace(config, retention_protected_creators=protected + (creator,)))
        print(f"Protected creator: @{creator}", file=stdout)
        return 0
    if creator not in protected:
        raise CreatorIdentityError(f"creator is not protected: @{creator}")
    store.save(replace(config, retention_protected_creators=tuple(
        item for item in protected if item != creator)))
    print(f"Unprotected creator: @{creator}", file=stdout)
    return 0
