#!/usr/bin/env python3
"""Validate individually decodable FLV parts from one TikREC session."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, TextIO

from tikrec.part_validation import validate_part


def validate_parts(
    parts_directory: Path,
    *,
    ffprobe: str = "ffprobe",
    runner: Callable[..., Any] = subprocess.run,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
) -> int:
    """Validate each retained FLV part and print available timing metadata."""
    parts_directory = Path(parts_directory)
    if not parts_directory.is_dir():
        print(f"tikrec-validate: not a parts directory: {parts_directory}", file=stderr)
        return 2
    parts = tuple(sorted(parts_directory.glob("part-*.flv")))
    if not parts:
        print(f"tikrec-validate: no retained FLV parts in {parts_directory}", file=stderr)
        return 2

    failures = 0
    for part in parts:
        try:
            problems, warnings = validate_part(part, ffprobe, runner)
        except OSError as error:
            print(f"FAIL {part.name}: could not start FFprobe: {error}", file=stderr)
            return 2
        for check, warning in warnings:
            print(f"WARNING {part.name} {check}: {warning}", file=stderr)
        if not problems:
            print(f"PASS {part.name}", file=stdout)
            continue
        failures += 1
        print(f"FAIL {part.name}", file=stdout)
        for check, reason in problems:
            print(f"{part.name} {check} check failed: {reason}", file=stderr)

    _print_timing_summary(parts_directory / "connections.jsonl", stdout, stderr)
    print(f"{len(parts) - failures}/{len(parts)} parts passed", file=stdout)
    return 1 if failures else 0


def _print_timing_summary(path: Path, stdout: TextIO, stderr: TextIO) -> None:
    if not path.is_file():
        return
    try:
        records = [json.loads(line) for line in path.read_text().splitlines() if line]
    except (OSError, json.JSONDecodeError) as error:
        print(f"tikrec-validate: could not read {path.name}: {error}", file=stderr)
        return
    print("Timing summary:", file=stdout)
    for record in records:
        prefix = f"connection {record.get('connection')} ({record.get('outcome')})"
        timings = record.get("part_timings", [])
        if not timings:
            print(f"  {prefix}: no retained part timings", file=stdout)
            continue
        for timing in timings:
            print(
                f"  {prefix} {timing.get('name')}: "
                f"config={timing.get('configuration_timestamp')} "
                f"first-media={timing.get('first_media_timestamp')} "
                f"keyframe={timing.get('first_keyframe_timestamp')} "
                f"gate={timing.get('keyframe_gate_duration')}ms "
                f"last={timing.get('last_tag_timestamp')}",
                file=stdout,
            )


def main(argv: Sequence[str] | None = None) -> int:
    """Run the individual-FLV validator from the command line."""
    parser = argparse.ArgumentParser(
        description="Validate retained FLV parts; do not pass a concatenated MP4."
    )
    parser.add_argument("parts_directory", metavar="PARTS_DIRECTORY")
    parser.add_argument("--ffprobe", default="ffprobe", help="FFprobe executable")
    arguments = parser.parse_args(argv)
    return validate_parts(Path(arguments.parts_directory), ffprobe=arguments.ffprobe)


if __name__ == "__main__":
    raise SystemExit(main())
