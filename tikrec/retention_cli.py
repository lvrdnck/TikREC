"""Owner-facing retention planning, protection, and explicit deletion routing."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import TextIO

from .configuration import ConfigurationStore, default_config_path
from .creator_identity import CreatorIdentityError, normalize_creator
from .retention_delete_cli import canonical_uuid, run_delete
from .retention_plan import plan_retention


def add_retention_command(subcommands) -> argparse.ArgumentParser:
    """Add local retention protection, planning, and one-session deletion."""
    retention = subcommands.add_parser("retention", help="protect, plan, or explicitly delete")
    actions = retention.add_subparsers(dest="retention_action", required=True)
    for action, description in (("protect", "protect one creator from retention"),
                                ("unprotect", "remove explicit protection")):
        command = actions.add_parser(action, help=description)
        command.add_argument("creator", metavar="CREATOR")
    actions.add_parser("protected", help="list explicitly protected creators")
    plan = actions.add_parser("plan", help="read-only preview of immediate sessions")
    plan.add_argument("root", nargs="?", metavar="ROOT")
    plan.add_argument("--json", action="store_true", help="print structured results")
    delete = actions.add_parser("delete", help="permanently delete one eligible session on Windows")
    delete.add_argument("session_id", type=_uuid_argument, metavar="SESSION_UUID")
    delete.add_argument("root", nargs="?", metavar="ROOT")
    delete.add_argument("--confirm", metavar="SESSION_UUID",
                        help="exact noninteractive confirmation UUID")
    return retention


def _uuid_argument(value: str) -> str:
    try:
        return canonical_uuid(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(str(error)) from error


def run_retention_command(arguments: argparse.Namespace, stdout: TextIO,
                          stderr: TextIO = sys.stderr, stdin: TextIO = sys.stdin,
                          **delete_options) -> int:
    """Run one local retention action with read-only planning or explicit consent."""
    path = Path(arguments.config_path) if arguments.config_path else default_config_path()
    store = ConfigurationStore(path)
    action = arguments.retention_action
    if action == "delete":
        return run_delete(arguments, store, stdout, stderr, stdin, **delete_options)
    config = store.load()
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
                _show_plan_item(item, stdout)
            if not result["sessions"]:
                print("No immediate TikREC sessions found.", file=stdout)
        return 0
    creator = normalize_creator(arguments.creator)
    def change(current):
        protected = current.retention_protected_creators
        if action == "protect":
            if creator in protected:
                raise CreatorIdentityError(f"creator is already protected: @{creator}")
            return replace(current, retention_protected_creators=protected + (creator,))
        if creator not in protected:
            raise CreatorIdentityError(f"creator is not protected: @{creator}")
        return replace(current, retention_protected_creators=tuple(
            item for item in protected if item != creator))
    # Read-modify-write under the policy lock keeps a concurrent config command
    # from accidentally restoring an older protection list.
    store.update(change)
    print(f"{'Protected' if action == 'protect' else 'Unprotected'} creator: @{creator}",
          file=stdout)
    return 0


def _show_plan_item(item: dict, stdout: TextIO) -> None:
    explanation = {
        "eligible": "completed and past the age threshold",
        "retained": "age retention disabled or session not old enough",
        "protected": "creator explicitly protected",
        "ineligible": "unsupported, unknown, or incomplete session",
        "needs_attention": "conflicting or unsafe evidence needs inspection",
    }[item["classification"]]
    ended = "unknown"
    if type(item["ended_at"]) in {int, float}:
        try:
            ended = datetime.fromtimestamp(item["ended_at"], timezone.utc).isoformat().replace(
                "+00:00", "Z")
        except (OverflowError, OSError, ValueError):
            pass
    protection = ("protected (protected_creator)" if item["protected"] is True
                  else "not protected" if item["protected"] is False else "unknown")
    number = lambda value: "unknown" if value is None else str(value)
    print(f"{item['parts_directory']}: {item['classification']} ({item['reason']}) — "
          f"{explanation}", file=stdout)
    print(f"  session={item['session_id'] or 'unknown'}; "
          f"creator={item['creator'] or 'unknown'}; ended={ended}; "
          f"protection={protection}", file=stdout)
    print(f"  final MP4={item['output_path'] or 'unknown'}; "
          f"retained parts={item['parts_directory']}", file=stdout)
    print("  files=" + number(item["file_count"]) +
          "; FLV parts=" + number(item["flv_part_count"]) +
          "; final bytes=" + number(item["final_output_bytes"]) +
          "; retained-parts bytes=" + number(item["retained_parts_bytes"]) +
          "; total bytes=" + number(item["total_file_bytes"]), file=stdout)
