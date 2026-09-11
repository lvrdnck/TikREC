#!/usr/bin/env python3
"""Compatibility wrapper for TikREC's supported recording validator."""

from __future__ import annotations

import argparse
import subprocess
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, TextIO

from tikrec.validation import validate_target
from tikrec.validation_report import render_validation


def validate_parts(
    parts_directory: Path,
    *,
    deep: bool = False,
    ffprobe: str = "ffprobe",
    runner: Callable[..., Any] = subprocess.run,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
) -> int:
    """Validate a parts directory through the supported read-only layer."""
    del stderr  # The shared renderer keeps one deterministic human output stream.
    result = validate_target(
        Path(parts_directory), deep=deep, ffprobe=ffprobe, runner=runner
    )
    print(render_validation(result), file=stdout)
    return 0 if result.passed else 1


def main(argv: Sequence[str] | None = None) -> int:
    """Run the compatibility validator from the command line."""
    parser = argparse.ArgumentParser(
        description="Validate retained FLV parts; prefer `tikrec validate`."
    )
    parser.add_argument("parts_directory", metavar="PARTS_DIRECTORY")
    parser.add_argument("--deep", action="store_true", help="fully decode completed output")
    parser.add_argument("--ffprobe", default="ffprobe", help="FFprobe executable")
    arguments = parser.parse_args(argv)
    return validate_parts(
        Path(arguments.parts_directory), deep=arguments.deep, ffprobe=arguments.ffprobe
    )


if __name__ == "__main__":
    raise SystemExit(main())
