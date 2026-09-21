"""Command-line entry point for direct-FLV and public TikTok LIVE recording."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import TextIO

from . import __version__
from .capture import CaptureError, CaptureResult, capture_url
from .config_cli import add_config_command, run_config_command
from .control_cli import add_control_commands, run_control_command
from .diagnostics import add_debug_arguments, parse_arguments, print_unexpected_traceback
from .finalize import finalize_parts
from .live import capture_live
from .manifest import SessionManifest
from .output_naming import local_recording_paths
from .progress import LiveProgress
from .recovery_cli import add_recovery_command, run_recovery_command
from .recovery_discovery import discover_recovery_candidates
from .recovery_options import effective_retry_policy, recovery_window_argument
from .remote import RemoteError
from .service import serve
from .tiktok import TikTokResolutionError, resolve_live_url
from .validation import validate_target
from .validation_cli import add_validation_command, effective_validation_mode
from .validation_report import ValidationResult, render_validation


def main(
    argv: Sequence[str] | None = None,
    *,
    capture: Callable[..., CaptureResult] = capture_url,
    live_capture: Callable[..., CaptureResult] = capture_live,
    resolver: Callable[[str], str] = resolve_live_url,
    finalizer: Callable[..., Path] = finalize_parts,
    validator: Callable[..., ValidationResult] = validate_target,
    recovery_discoverer: Callable = discover_recovery_candidates,
    service_runner: Callable = serve,
    remote_opener: Callable | None = None,
    naming_clock: Callable | None = None,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
) -> int:
    """Run the small recording CLI and return a conventional process code."""
    parser = _parser()
    try:
        arguments = parse_arguments(parser, argv)
    except SystemExit as error:
        return int(error.code)
    except KeyboardInterrupt:
        print("tikrec: interrupted", file=stderr)
        return 130
    live_progress: LiveProgress | None = None
    try:
        if arguments.command in {"serve", "remote"}:
            return run_control_command(arguments, stdout, service_runner=service_runner,
                                       remote_opener=remote_opener)
        if arguments.command == "config":
            return run_config_command(arguments, stdout)
        if arguments.command == "resolve":
            direct_url = resolver(arguments.url)
            print(direct_url, file=stdout)
            return 0
        if arguments.command == "validate":
            deep = effective_validation_mode(arguments.validation_mode, arguments.config_path) == "deep"
            result = validator(Path(arguments.target), deep=deep)
            if arguments.json:
                print(json.dumps(result.as_dict(), indent=2, sort_keys=True), file=stdout)
            else:
                print(render_validation(result), file=stdout)
            return 0 if result.passed else 1
        if arguments.command == "recover":
            return run_recovery_command(
                arguments, stdout, discoverer=recovery_discoverer, validator=validator,
                finalizer=finalizer,
            )
        if arguments.command == "finalize":
            output_path = Path(arguments.output)
            live_progress = LiveProgress(stdout)
            _finalize_directory(
                Path(arguments.parts_directory),
                output_path,
                finalizer,
                live_progress.event,
            )
            return 0
        output_path, parts_directory = local_recording_paths(
            arguments.command, arguments.url, arguments.output,
            config_path=arguments.config_path, clock=naming_clock,
        )
        raw_copy_dir = Path(arguments.raw_copy) if arguments.raw_copy is not None else None
        warning = lambda message: print(f"tikrec: warning: {message}", file=stderr)
        capture_function = live_capture if arguments.command == "live" else capture
        if arguments.command == "live":
            live_progress = LiveProgress(stdout)
            retry_policy = effective_retry_policy(
                arguments.recovery_window_seconds, arguments.config_path
            )
            result = capture_function(
                arguments.url,
                parts_directory=parts_directory,
                output_path=output_path,
                progress=live_progress.event,
                heartbeat=live_progress.heartbeat,
                raw_copy_dir=raw_copy_dir,
                warning=warning,
                retry_policy=retry_policy,
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
            if result.output_path is not None:
                message = (
                    f"tikrec: interrupted; output written to {result.output_path}; "
                    f"retained parts in {parts_directory}"
                )
            else:
                message = f"tikrec: interrupted; retained parts in {parts_directory}"
            _print_final(live_progress, message, stderr)
            return 130
        _print_final(live_progress, f"recorded {result.output_path}", stdout)
        return 0
    except KeyboardInterrupt:
        _print_final(live_progress, "tikrec: interrupted", stderr)
        return 130
    except (CaptureError, TikTokResolutionError, RemoteError, OSError, ValueError) as error:
        _print_final(live_progress, f"tikrec: {_one_line_error(error)}", stderr)
        return 1
    except Exception as error:
        _print_final(
            live_progress,
            f"tikrec: unexpected {type(error).__name__}: {_one_line_error(error)}",
            stderr,
        )
        print_unexpected_traceback(
            arguments.debug_tracebacks, arguments.config_path, stderr
        )
        return 1
    finally:
        if live_progress is not None:
            live_progress.close()


def _one_line_error(error: Exception) -> str:
    return " ".join(str(error).split())

def _print_final(progress: LiveProgress | None, message: str, stream: TextIO) -> None:
    """Clear an active heartbeat before writing a final CLI result."""
    if progress is not None:
        progress.clear()
    print(message, file=stream)

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
    parser = argparse.ArgumentParser(
        prog="tikrec",
        description="Record public TikTok LIVE streams or advanced direct media sources.",
        epilog=(
            "Normal use:\n"
            "  tikrec live https://www.tiktok.com/@creator/live\n\n"
            "Configure an output directory for automatic naming, or pass --output. "
            "Use `live` for a TikTok LIVE page. `record` is for an advanced direct "
            "FLV/media URL, not a TikTok page."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    add_debug_arguments(parser)
    parser.add_argument("--config", dest="config_path", metavar="FILE",
                        help="use an explicit per-user configuration file")
    subcommands = parser.add_subparsers(dest="command", required=True)
    add_control_commands(subcommands)
    config = add_config_command(subcommands)
    record = subcommands.add_parser(
        "record",
        help="advanced: record a direct FLV/media URL, not a TikTok page",
        description=(
            "Record an advanced direct FLV/media URL. This command does not accept "
            "a TikTok LIVE page URL; use `tikrec live` for a public TikTok LIVE page."
        ),
    )
    record.add_argument("url", metavar="DIRECT_FLV_URL", help="direct FLV/media URL, not a TikTok page")
    record.add_argument("--output", required=True, metavar="FILE", help="output MP4 file")
    record.add_argument("--raw-copy", metavar="DIR", help="save unmodified connection bytes")
    finalize = subcommands.add_parser("finalize", help="stitch retained FLV parts")
    finalize.add_argument("parts_directory", metavar="PARTS_DIRECTORY")
    finalize.add_argument("--output", required=True, metavar="FILE")
    resolve = subcommands.add_parser(
        "resolve",
        help="print the direct media URL for a TikTok LIVE page",
        description="Resolve a public TikTok LIVE page URL and print its direct FLV/media URL.",
    )
    resolve.add_argument("url", metavar="TIKTOK_LIVE_URL", help="public TikTok LIVE page URL")
    live = subcommands.add_parser(
        "live",
        help="normal use: record a public TikTok LIVE page",
        description="Record one manually selected public TikTok LIVE from its page URL.",
        epilog=(
            "Examples:\n"
            "  tikrec live https://www.tiktok.com/@creator/live\n"
            "  tikrec live https://www.tiktok.com/@creator/live --output creator.mp4\n\n"
            "Without --output, a configured output directory is required and TikREC "
            "uses creator-YYYYMMDD-HHMMSS.mp4."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    live.add_argument("url", metavar="TIKTOK_LIVE_URL", help="public TikTok LIVE page URL")
    live.add_argument("--output", metavar="FILE",
                      help="output MP4 file; omit for configured automatic naming")
    live.add_argument("--raw-copy", metavar="DIR", help="save unmodified connection bytes")
    live.add_argument("--recovery-window-seconds", type=recovery_window_argument,
                      metavar="SECONDS", help="override the 60-3600 second recovery window")
    validate = add_validation_command(subcommands)
    recover = add_recovery_command(subcommands)
    for command in (record, finalize, resolve, live, validate, recover, config):
        # Accept the global diagnostic flag after a subcommand as well.
        add_debug_arguments(command, suppress_default=True)
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
