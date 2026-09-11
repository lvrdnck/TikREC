"""Command-line entry point for direct-FLV and public TikTok LIVE recording."""

from __future__ import annotations

import argparse
import json
import sys
import traceback
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import TextIO

from . import __version__
from .capture import CaptureError, CaptureResult, capture_url
from .finalize import finalize_parts
from .live import capture_live
from .manifest import SessionManifest
from .progress import LiveProgress
from .tiktok import TikTokResolutionError, resolve_live_url
from .validation import validate_target
from .validation_report import ValidationResult, render_validation


def main(
    argv: Sequence[str] | None = None,
    *,
    capture: Callable[..., CaptureResult] = capture_url,
    live_capture: Callable[..., CaptureResult] = capture_live,
    resolver: Callable[[str], str] = resolve_live_url,
    finalizer: Callable[..., Path] = finalize_parts,
    validator: Callable[..., ValidationResult] = validate_target,
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

    live_progress: LiveProgress | None = None
    try:
        if arguments.command == "resolve":
            direct_url = resolver(arguments.url)
            print(direct_url, file=stdout)
            return 0

        if arguments.command == "validate":
            result = validator(Path(arguments.target), deep=arguments.deep)
            if arguments.json:
                print(json.dumps(result.as_dict(), indent=2, sort_keys=True), file=stdout)
            else:
                print(render_validation(result), file=stdout)
            return 0 if result.passed else 1

        output_path = Path(arguments.output)
        if arguments.command == "finalize":
            live_progress = LiveProgress(stdout)
            _finalize_directory(
                Path(arguments.parts_directory),
                output_path,
                finalizer,
                live_progress.event,
            )
            return 0

        parts_directory = output_path.with_name(f"{output_path.stem}.parts")
        raw_copy_dir = Path(arguments.raw_copy) if arguments.raw_copy is not None else None
        warning = lambda message: print(f"tikrec: warning: {message}", file=stderr)
        capture_function = live_capture if arguments.command == "live" else capture
        if arguments.command == "live":
            live_progress = LiveProgress(stdout)
            result = capture_function(
                arguments.url,
                parts_directory=parts_directory,
                output_path=output_path,
                progress=live_progress.event,
                heartbeat=live_progress.heartbeat,
                raw_copy_dir=raw_copy_dir,
                warning=warning,
            )
        else:
            result = capture_function(
                arguments.url,
                parts_directory=parts_directory,
                output_path=output_path,
                raw_copy_dir=raw_copy_dir,
                warning=warning,
            )
        if result.interrupted:
            if live_progress is not None:
                live_progress.clear()
            if result.output_path is not None:
                print(
                    f"tikrec: interrupted; output written to {result.output_path}; "
                    f"retained parts in {parts_directory}",
                    file=stderr,
                )
            else:
                print(f"tikrec: interrupted; retained parts in {parts_directory}", file=stderr)
            return 130
        print(f"recorded {result.output_path}", file=stdout)
        return 0
    except KeyboardInterrupt:
        if live_progress is not None:
            live_progress.clear()
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
    finally:
        if live_progress is not None:
            live_progress.close()


def _one_line_error(error: Exception) -> str:
    return " ".join(str(error).split())


def _finalize_directory(
    parts_directory: Path,
    output_path: Path,
    finalizer: Callable[..., Path],
    progress: Callable[[str], None],
) -> Path:
    """Finalize retained FLV parts without modifying their directory."""
    if not parts_directory.is_dir():
        raise CaptureError(f"parts directory does not exist: {parts_directory}")
    parts = tuple(sorted(parts_directory.glob("part-*.flv")))
    if not parts:
        raise CaptureError(f"no completed FLV parts in: {parts_directory}")
    manifest = _load_manifest(parts_directory / "session.json", progress)
    if manifest is not None:
        try:
            manifest.mark_recovery(output_path, parts)
        except (OSError, ValueError) as error:
            progress(f"warning: session manifest could not be updated: {error}")
            manifest = None
    try:
        progress("finalizing")
        if finalizer is finalize_parts:
            output = finalizer(parts, output_path, progress=progress)
        else:
            output = finalizer(parts, output_path)
    except KeyboardInterrupt:
        if manifest is not None:
            _finish_recovery(
                manifest, parts, "interrupted", progress, error="finalization interrupted"
            )
        raise
    except Exception as error:
        if manifest is not None:
            _finish_recovery(manifest, parts, "failed", progress, error=error)
        raise CaptureError(f"finalization failed: {error}", parts) from error
    progress(f"output written: {output} ({output.stat().st_size} bytes)")
    if manifest is not None:
        _finish_recovery(manifest, parts, "completed", progress, output_path=output)
    return output


def _load_manifest(
    path: Path,
    progress: Callable[[str], None],
) -> SessionManifest | None:
    """Load recovery metadata without making older or damaged sessions unusable."""
    try:
        return SessionManifest.load(path)
    except (OSError, ValueError) as error:
        progress(f"warning: session manifest could not be read: {error}")
        return None


def _finish_recovery(
    manifest: SessionManifest,
    parts: tuple[Path, ...],
    status: str,
    progress: Callable[[str], None],
    *,
    output_path: Path | None = None,
    error: BaseException | str | None = None,
) -> None:
    """Keep a manifest write problem from hiding the finalization result."""
    try:
        manifest.finish_recovery(parts, status, output_path=output_path, error=error)
    except (OSError, ValueError) as manifest_error:
        progress(f"warning: session manifest could not be updated: {manifest_error}")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tikrec")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--debug", action="store_true", help="print unexpected-error tracebacks")
    subcommands = parser.add_subparsers(dest="command", required=True)
    record = subcommands.add_parser("record", help="record one direct FLV URL")
    record.add_argument("url", metavar="DIRECT_FLV_URL")
    record.add_argument("--output", required=True, metavar="FILE")
    record.add_argument("--raw-copy", metavar="DIR", help="save unmodified connection bytes")
    finalize = subcommands.add_parser("finalize", help="stitch retained FLV parts")
    finalize.add_argument("parts_directory", metavar="PARTS_DIRECTORY")
    finalize.add_argument("--output", required=True, metavar="FILE")
    resolve = subcommands.add_parser("resolve", help="resolve one public TikTok LIVE page")
    resolve.add_argument("url", metavar="TIKTOK_LIVE_URL")
    live = subcommands.add_parser("live", help="record a public TikTok LIVE page")
    live.add_argument("url", metavar="TIKTOK_LIVE_URL")
    live.add_argument("--output", required=True, metavar="FILE")
    live.add_argument("--raw-copy", metavar="DIR", help="save unmodified connection bytes")
    validate = subcommands.add_parser("validate", help="check recording health")
    validate.add_argument("target", metavar="TARGET")
    validate.add_argument("--deep", action="store_true", help="fully decode completed output")
    validate.add_argument("--json", action="store_true", help="print structured results")
    for command in (record, finalize, resolve, live, validate):
        # Accept the global diagnostic flag after a subcommand as well.
        command.add_argument("--debug", action="store_true", default=argparse.SUPPRESS)
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
