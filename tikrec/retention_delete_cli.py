"""Explicit local one-session retention deletion and truthful CLI outcomes."""

from __future__ import annotations

import sys
import time
import uuid
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import TextIO

from .configuration import ConfigurationStore
from .media import MediaInfo, inspect_media
from .retention_execute import RetentionProgress, execute_retention
from .retention_mutation import require_identity_removal
from .retention_preview import RetentionPreview, prepare_preview


def canonical_uuid(value: str) -> str:
    """Accept only the exact lowercase canonical target spelling."""
    try:
        if str(uuid.UUID(value)) == value:
            return value
    except (ValueError, AttributeError):
        pass
    raise ValueError("retention target must be a canonical lowercase session UUID")


def run_delete(arguments, store: ConfigurationStore, stdout: TextIO,
               stderr: TextIO, stdin: TextIO = sys.stdin, *,
               clock: Callable[[], float] = time.time,
               media_inspector: Callable[[Path], MediaInfo | None] = inspect_media,
               job_paths: tuple[Path, Path] | None = None,
               audit_path: Path | None = None) -> int:
    """Preview, confirm, freshly execute, and classify one retention attempt."""
    session_id = arguments.session_id
    root = Path(arguments.root) if arguments.root is not None else None
    progress = RetentionProgress()
    try:
        # Platform refusal precedes even a read-only preview, lock, or audit.
        try:
            require_identity_removal()
        except ValueError as error:
            raise ValueError("v0.11 destructive retention is Windows-only; "
                             "retention plan remains available") from error
        config = store.load()
        root = root if root is not None else config.output_directory
        if root is None:
            raise ValueError("retention delete requires ROOT or configured output_directory")
        if arguments.confirm is not None and arguments.confirm != session_id:
            raise ValueError("confirmation UUID does not exactly match target")
        preview = prepare_preview(root, session_id, store, job_paths=job_paths,
                                  clock=clock, media_inspector=media_inspector)
        _show_preview(preview, stdout)
        if arguments.confirm is None and not _typed_confirmation(stdin, stdout, session_id):
            raise ValueError("exact session UUID confirmation was not provided")
        operation_id = execute_retention(
            root, session_id, store, audit_path=audit_path, job_paths=job_paths,
            clock=clock, media_inspector=media_inspector,
            preview_guard=preview.guard, progress=progress)
    except BaseException as error:
        if progress.completed_durable:
            return _completed_after_cleanup(session_id, preview, progress, error, stderr)
        # The executor publishes the body fault before context cleanup can
        # replace it; a later cleanup error is only secondary evidence.
        primary = progress.operation_error if progress.operation_error is not None else error
        cleanup_error = error if primary is not error else None
        if progress.intent_sync_started:
            return _incomplete(progress, session_id, root, primary, stderr,
                               cleanup_error=cleanup_error)
        if isinstance(primary, KeyboardInterrupt):
            _diagnose(stderr, [f"tikrec retention delete: interrupted before intent; "
                               f"session={session_id}; root={root or '<unconfigured>'}"])
            return 130
        if isinstance(primary, Exception):
            _refused(session_id, root, primary, stderr,
                     intent_attempted=progress.intent_attempted)
            return 1
        raise primary
    # The executor has returned only after the completed event synced. Display
    # failures cannot turn that completed deletion into an incomplete result.
    return _completed(session_id, preview, operation_id, progress.audit_path,
                      stdout, stderr)


def _completed(session_id: str, preview: RetentionPreview, operation_id: str,
               audit_path: Path | None, stdout: TextIO, stderr: TextIO) -> int:
    """Keep a durable completed result truthful if its normal display fails."""
    try:
        print(f"COMPLETE: deleted session {session_id} from {preview.root}", file=stdout)
        print(f"Operation ID: {operation_id}", file=stdout)
        print(f"Audit: {audit_path}", file=stdout)
        stdout.flush()
    except BaseException as error:
        # A broken diagnostic channel must not change the known completed exit.
        try:
            print(f"COMPLETE: deleted session {session_id} from {preview.root}",
                  file=stderr)
            print(f"Output error: {type(error).__name__}: {_one_line(error)}",
                  file=stderr)
            print(f"Operation ID: {operation_id}", file=stderr)
            print(f"Audit: {audit_path}", file=stderr)
            stderr.flush()
        except BaseException:
            pass
    return 0


def _completed_after_cleanup(session_id: str, preview: RetentionPreview,
                             progress: RetentionProgress, error: BaseException,
                             stderr: TextIO) -> int:
    """Keep synced completion authoritative when later executor cleanup fails."""
    try:
        _diagnose(stderr, [
            f"COMPLETE: deleted session {session_id} from {preview.root}",
            f"Cleanup error: {type(error).__name__}: {_one_line(error)}",
            f"Operation ID: {progress.operation_id}",
            f"Audit: {progress.audit_path}",
        ])
    except BaseException:
        # Formatting or diagnostic failures cannot replace proven completion.
        pass
    return 0


def _show_preview(preview: RetentionPreview, stdout: TextIO) -> None:
    """Show the exact target and scale of permanent removal before consent."""
    ended = datetime.fromtimestamp(preview.ended_at, timezone.utc).isoformat().replace(
        "+00:00", "Z")
    print("Retention deletion preview — permanent", file=stdout)
    print(f"Root: {preview.root}", file=stdout)
    print(f"Creator: @{preview.creator}    Session: {preview.session_id}", file=stdout)
    print(f"Ended: {ended}    State: eligible (age threshold reached; not protected)",
          file=stdout)
    print(f"Final MP4: {preview.output}", file=stdout)
    print(f"Retained parts: {preview.parts}", file=stdout)
    print(f"Removal: about {preview.total_file_bytes} bytes across "
          f"{preview.file_count} files, then the empty parts directory", file=stdout)
    print("Order: retained artifacts and controls first; final MP4 last", file=stdout)
    print("Deletion is permanent. TikREC will recheck eligibility and evidence "
          "after confirmation.", file=stdout)


def _typed_confirmation(stdin: TextIO, stdout: TextIO, session_id: str) -> bool:
    """Require an interactive exact UUID, stripping only its terminal newline."""
    if not stdin.isatty():
        return False
    print(f"Type the exact session UUID to delete: {session_id}", file=stdout)
    stdout.flush()
    value = stdin.readline()
    if value.endswith("\r\n"):
        value = value[:-2]
    elif value.endswith(("\n", "\r")):
        value = value[:-1]
    return value == session_id


def _refused(session_id: str, root: Path | None, error: Exception,
             stderr: TextIO, *, intent_attempted: bool = False) -> None:
    """Report a pre-intent refusal without implying a journaled operation."""
    lines = []
    if intent_attempted:
        lines.append("Audit intent durability was not confirmed; no artifact "
                     "removal was attempted.")
    lines.extend((f"REFUSED: session={session_id}; root={root or '<unconfigured>'}; "
                  f"reason={_one_line(error)}",
                  "No deletion operation was started."))
    _diagnose(stderr, lines)


def _incomplete(progress: RetentionProgress, session_id: str, root: Path | None,
                error: BaseException, stderr: TextIO, *,
                cleanup_error: BaseException | None = None) -> int:
    """Report after-intent uncertainty without changing or repairing artifacts."""
    state = "PARTIAL" if progress.deleted_count or progress.removal_uncertain else "FAILED"
    lines = [f"{state}: session={session_id}; root={root}; reason={_one_line(error)}",
             f"Operation ID: {progress.operation_id or 'unknown'}"]
    if cleanup_error is not None:
        lines.append(f"Cleanup error: {type(cleanup_error).__name__}: "
                     f"{_one_line(cleanup_error)}")
    if progress.audit_path is not None:
        lines.append(f"Audit: {progress.audit_path}")
    if not progress.intent_durable:
        lines.append("Audit intent durability was not confirmed; the journal may "
                     "contain an intent.")
    elif progress.audit_uncertain:
        lines.append("Audit state may be incomplete or unavailable.")
    else:
        lines.append("The audit record preserves the known event sequence.")
    lines.append("Inspect the audit and filesystem before any fresh retention "
                 "decision; TikREC will not retry or resume automatically.")
    _diagnose(stderr, lines)
    return 3


def _diagnose(stderr: TextIO, lines: list[str]) -> None:
    """Make one bounded diagnostic attempt without altering the known result."""
    try:
        stderr.write("\n".join(lines) + "\n")
        stderr.flush()
    except BaseException:
        pass


def _one_line(error: BaseException) -> str:
    return " ".join(str(error).split()) or type(error).__name__
