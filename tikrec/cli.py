"""Command-line entry point for direct-FLV and public TikTok LIVE recording."""

from __future__ import annotations

import argparse
import sys
import traceback
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import TextIO

from .capture import CaptureError, CaptureResult, capture_url
from .live import capture_live
from .tiktok import TikTokResolutionError, resolve_live_url


def main(
    argv: Sequence[str] | None = None,
    *,
    capture: Callable[..., CaptureResult] = capture_url,
    live_capture: Callable[..., CaptureResult] = capture_live,
    resolver: Callable[[str], str] = resolve_live_url,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
) -> int:
    """Run the small recording CLI and return a conventional process code."""
    parser = _parser()
    try:
        arguments = parser.parse_args(argv)
    except SystemExit as error:
        return int(error.code)
    except KeyboardInterrupt:
        print("tikrec: interrupted", file=stderr)
        return 130

    try:
        if arguments.command == "resolve":
            direct_url = resolver(arguments.url)
            print(direct_url, file=stdout)
            return 0

        output_path = Path(arguments.output)
        parts_directory = output_path.with_name(f"{output_path.stem}.parts")
        capture_function = live_capture if arguments.command == "live" else capture
        if arguments.command == "live":
            # Flush each update so an unattended recording stays observable.
            result = capture_function(
                arguments.url,
                parts_directory=parts_directory,
                output_path=output_path,
                progress=lambda message: print(message, file=stdout, flush=True),
            )
        else:
            result = capture_function(
                arguments.url,
                parts_directory=parts_directory,
                output_path=output_path,
            )
        if result.interrupted:
            print(f"tikrec: interrupted; retained parts in {parts_directory}", file=stderr)
            return 130
        print(f"recorded {result.output_path}", file=stdout)
        return 0
    except KeyboardInterrupt:
        print("tikrec: interrupted", file=stderr)
        return 130
    except (CaptureError, TikTokResolutionError, OSError, ValueError) as error:
        print(f"tikrec: {_one_line_error(error)}", file=stderr)
        return 1
    except Exception as error:
        print(f"tikrec: unexpected {type(error).__name__}: {_one_line_error(error)}", file=stderr)
        if arguments.debug:
            traceback.print_exc(file=stderr)
        return 1


def _one_line_error(error: Exception) -> str:
    return " ".join(str(error).split())


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tikrec")
    parser.add_argument("--debug", action="store_true", help="print unexpected-error tracebacks")
    subcommands = parser.add_subparsers(dest="command", required=True)
    record = subcommands.add_parser("record", help="record one direct FLV URL")
    record.add_argument("url", metavar="DIRECT_FLV_URL")
    record.add_argument("--output", required=True, metavar="FILE")
    resolve = subcommands.add_parser("resolve", help="resolve one public TikTok LIVE page")
    resolve.add_argument("url", metavar="TIKTOK_LIVE_URL")
    live = subcommands.add_parser("live", help="record a public TikTok LIVE page")
    live.add_argument("url", metavar="TIKTOK_LIVE_URL")
    live.add_argument("--output", required=True, metavar="FILE")
    for command in (record, resolve, live):
        # Accept the global diagnostic flag after a subcommand as well.
        command.add_argument("--debug", action="store_true", default=argparse.SUPPRESS)
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
