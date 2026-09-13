"""Durable high-level metadata for one recording session."""

from __future__ import annotations

import json
from copy import deepcopy
import os
import re
import time
import uuid
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

from . import __version__
from .media import MediaInfo, inspect_media


SCHEMA_VERSION = 1
_URL_PATTERN = re.compile(r"https?://\S+")


class SessionManifest:
    """Create and atomically update ``session.json`` for one capture."""

    def __init__(
        self,
        parts_directory: Path,
        output_path: Path | None,
        source_type: str,
        *,
        clock: Callable[[], float] = time.time,
        media_inspector: Callable[[Path], MediaInfo | None] = lambda path: inspect_media(path),
        session_id: str | None = None,
    ) -> None:
        self.path = Path(parts_directory) / "session.json"
        self._parts_directory = Path(parts_directory)
        self._output_path = Path(output_path) if output_path is not None else None
        self._source_type = source_type
        self._clock = clock
        self._media_inspector = media_inspector
        self._session_id = session_id
        self._values: dict[str, Any] | None = None

    @property
    def active(self) -> bool:
        """Return whether this session has created its initial manifest."""
        return self._values is not None

    def snapshot(self) -> dict[str, Any]:
        """Return independent manifest facts for read-only resume preflight."""
        return deepcopy(self._require_values())

    def resume_capture(self, parts: Iterable[Path], connection_count: int,
                       *, output_path: Path | None = None) -> None:
        """Reopen validated capture while preserving identity and original start time."""
        values = self._require_values()
        values.update(status="recording", ended_at=None, elapsed_seconds=None,
                      interrupted=False, recovery_performed=True, error=None,
                      part_count=len(tuple(parts)), connection_count=connection_count,
                      reconnect_count=max(0, connection_count - 1))
        if output_path is not None:
            values["output_path"] = str(output_path)
        # Capture-only resume deliberately does not request a new finalization attempt.
        values["finalization"] = {
            "status": "pending" if output_path is not None else "not_requested", "error": None,
        }
        self._write()

    def start(self, *, connection_count: int = 0) -> None:
        """Initialize a recording-state manifest after the session directory exists."""
        started_at = self._clock()
        self._values = {
            "schema_version": SCHEMA_VERSION,
            "session_id": self._session_id or str(uuid.uuid4()),
            "tikrec_version": __version__,
            "source_type": self._source_type,
            "started_at": started_at,
            "ended_at": None,
            "elapsed_seconds": None,
            "status": "recording",
            "parts_directory": str(self._parts_directory),
            "output_path": None if self._output_path is None else str(self._output_path),
            "part_count": 0,
            "connection_count": connection_count,
            "reconnect_count": max(0, connection_count - 1),
            "interrupted": False,
            "recovery_performed": False,
            "finalization": {
                "status": "not_requested" if self._output_path is None else "pending",
                "error": None,
            },
            "media": _media_values(None),
            "error": None,
        }
        self._write()

    def update_capture(
        self,
        parts: Iterable[Path],
        *,
        connection_count: int | None = None,
    ) -> None:
        """Persist high-level progress while capture remains active."""
        values = self._require_values()
        values["part_count"] = len(tuple(parts))
        if connection_count is not None:
            values["connection_count"] = connection_count
            values["reconnect_count"] = max(0, connection_count - 1)
        self._write()

    def mark_finalizing(self, parts: Iterable[Path]) -> None:
        """Record that capture ended and requested finalization has started."""
        self.update_capture(parts)
        self._require_values()["finalization"] = {"status": "running", "error": None}
        self._write()

    def finish(
        self,
        status: str,
        parts: Iterable[Path],
        *,
        output_path: Path | None = None,
        interrupted: bool = False,
        finalization_status: str | None = None,
        error: BaseException | str | None = None,
    ) -> None:
        """Finalize lifecycle, result, output, and optional media information."""
        values = self._require_values()
        completed_parts = tuple(parts)
        ended_at = self._clock()
        values.update({
            "ended_at": ended_at,
            "elapsed_seconds": max(0.0, ended_at - float(values["started_at"])),
            "status": status,
            "part_count": len(completed_parts),
            "interrupted": interrupted,
            "error": _safe_reason(error),
        })
        if output_path is not None:
            values["output_path"] = str(output_path)
        if finalization_status is not None:
            finalization_error = _safe_reason(error) if finalization_status == "failed" else None
            values["finalization"] = {
                "status": finalization_status,
                "error": finalization_error,
            }
        self._inspect_output(output_path)
        self._write()

    def complete(
        self,
        parts: Iterable[Path],
        *,
        output_path: Path | None = None,
        interrupted: bool = False,
        finalization_status: str | None = None,
        error: BaseException | str | None = None,
    ) -> None:
        """Finish a successful or interrupted capture with consistent status."""
        self.finish(
            "interrupted" if interrupted else "completed",
            parts,
            output_path=output_path,
            interrupted=interrupted,
            finalization_status=finalization_status,
            error=error,
        )

    def fail(
        self,
        parts: Iterable[Path],
        error: BaseException | str,
        *,
        finalization_status: str | None = None,
    ) -> None:
        """Finish a failed capture while preserving its safe failure reason."""
        self.finish(
            "failed",
            parts,
            finalization_status=finalization_status,
            error=error,
        )

    def mark_recovery(self, output_path: Path, parts: Iterable[Path]) -> None:
        """Record a manual finalization attempt for an existing v0.2 session."""
        values = self._require_values()
        values["recovery_performed"] = True
        values["output_path"] = str(output_path)
        values["part_count"] = len(tuple(parts))
        values["finalization"] = {"status": "running", "error": None}
        self._write()

    def finish_recovery(
        self,
        parts: Iterable[Path],
        status: str,
        *,
        output_path: Path | None = None,
        error: BaseException | str | None = None,
    ) -> None:
        """Finish manual finalization without rewriting the capture timeline."""
        values = self._require_values()
        values["part_count"] = len(tuple(parts))
        values["recovery_performed"] = True
        if values.get("status") == "recording":
            # A still-recording manifest proves the prior process never closed cleanly.
            values["status"] = "interrupted"
            values["interrupted"] = True
        if output_path is not None:
            values["output_path"] = str(output_path)
        values["finalization"] = {
            "status": status,
            "error": _safe_reason(error) if status == "failed" else None,
        }
        self._inspect_output(output_path)
        self._write()

    @classmethod
    def load(
        cls,
        path: Path,
        *,
        clock: Callable[[], float] = time.time,
        media_inspector: Callable[[Path], MediaInfo | None] = lambda path: inspect_media(path),
    ) -> SessionManifest | None:
        """Load an existing supported manifest, or return ``None`` for old sessions."""
        path = Path(path)
        if not path.is_file():
            return None
        values = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(values, dict) or values.get("schema_version") != SCHEMA_VERSION:
            raise ValueError(f"unsupported session manifest: {path}")
        output = values.get("output_path")
        manifest = cls(
            path.parent,
            Path(output) if isinstance(output, str) else None,
            str(values.get("source_type", "unknown")),
            clock=clock,
            media_inspector=media_inspector,
        )
        manifest._values = values
        return manifest

    def _require_values(self) -> dict[str, Any]:
        if self._values is None:
            raise RuntimeError("session manifest has not started")
        return self._values

    def _inspect_output(self, output_path: Path | None) -> None:
        media_path = Path(output_path) if output_path is not None else None
        if media_path is None or not media_path.is_file():
            return
        # Optional inspection evidence must never change capture success.
        try:
            self._require_values()["media"] = _media_values(self._media_inspector(media_path))
        except Exception:
            self._require_values()["media"] = _media_values(None)

    def _write(self) -> None:
        values = self._require_values()
        temporary = self.path.with_name(f".{self.path.name}.partial")
        try:
            with temporary.open("w", encoding="utf-8") as handle:
                json.dump(values, handle, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                # Flush complete JSON before the atomic replacement exposes it.
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise


def _media_values(info: MediaInfo | None) -> dict[str, str | int | None]:
    info = info or MediaInfo()
    return {
        "video_codec": info.video_codec,
        "audio_codec": info.audio_codec,
        "width": info.width,
        "height": info.height,
    }


def _safe_reason(error: BaseException | str | None) -> str | None:
    if error is None:
        return None
    return _URL_PATTERN.sub("[URL redacted]", str(error))
