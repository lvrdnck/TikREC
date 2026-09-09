"""Command-line entry point for recording one direct FLV stream."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import TextIO

from .capture import CaptureError, CaptureResult, capture_url


def main(
    argv: Sequence[str] | None = None,
    *,
    capture: Callable[..., CaptureResult] = capture_url,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
) -> int:
    """Run the small recording CLI and return a conventional process code."""
    parser = _parser()
    try:
        arguments = parser.parse_args(argv)
    except SystemExit as error:
        return int(error.code)

    output_path = Path(arguments.output)
    parts_directory = output_path.with_name(f"{output_path.stem}.parts")
    try:
        result = capture(
            arguments.url,
            parts_directory=parts_directory,
            output_path=output_path,
        )
    except (CaptureError, OSError, ValueError) as error:
        print(f"tikrec: {error}", file=stderr)
        return 1
    if result.interrupted:
        print(f"tikrec: interrupted; retained parts in {parts_directory}", file=stderr)
        return 130
    print(f"recorded {result.output_path}", file=stdout)
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tikrec")
    subcommands = parser.add_subparsers(dest="command", required=True)
    record = subcommands.add_parser("record", help="record one direct FLV URL")
    record.add_argument("url", metavar="DIRECT_FLV_URL")
    record.add_argument("--output", required=True, metavar="FILE")
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
