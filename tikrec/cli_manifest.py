"""Safe manifest updates for the manual finalize command."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from .manifest import SessionManifest


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
    input_decode: dict | None = None,
) -> None:
    """Keep a manifest write problem from hiding the finalization result."""
    try:
        manifest.finish_recovery(parts, status, output_path=output_path, error=error,
                                 input_decode=input_decode)
    except (OSError, ValueError) as manifest_error:
        progress(f"warning: session manifest could not be updated: {manifest_error}")
