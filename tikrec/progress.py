"""Render live-capture events and a terminal-aware recording heartbeat."""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path
from typing import TextIO


class LiveProgress:
    """Write scrolling events plus an elapsed-time and byte-count heartbeat."""

    def __init__(
        self,
        stdout: TextIO,
        *,
        clock: Callable[[], float] = time.monotonic,
        is_tty: bool | None = None,
        tty_interval: float = 5.0,
        redirected_interval: float = 60.0,
    ) -> None:
        self._stdout = stdout
        self._clock = clock
        self._started_at = clock()
        self._is_tty = stdout.isatty() if is_tty is None else is_tty
        self._interval = tty_interval if self._is_tty else redirected_interval
        self._last_heartbeat: float | None = None
        self._heartbeat_visible = False

    def event(self, message: str) -> None:
        """Write a normal event line without corrupting a TTY heartbeat."""
        if self._heartbeat_visible:
            # Erase the redrawn line before allowing the event into scrollback.
            self._write("\r\x1b[2K")
            self._heartbeat_visible = False
        self._write(f"{message}\n")

    def heartbeat(self, part: Path, byte_count: int) -> None:
        """Refresh status when the active writer has made enough progress."""
        now = self._clock()
        if self._last_heartbeat is not None and now - self._last_heartbeat < self._interval:
            return
        line = f"{_elapsed(now - self._started_at)}  {part.name}  {_size(byte_count)}"
        if self._is_tty:
            self._write(f"\r\x1b[2K{line}")
            self._heartbeat_visible = True
        else:
            self._write(f"{line}\n")
        self._last_heartbeat = now

    def close(self) -> None:
        """Finish a visible TTY heartbeat before control returns to the shell."""
        if self._heartbeat_visible:
            self._write("\n")
            self._heartbeat_visible = False

    def _write(self, text: str) -> None:
        self._stdout.write(text)
        self._stdout.flush()


def _elapsed(seconds: float) -> str:
    total_seconds = max(0, int(seconds))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def _size(byte_count: int) -> str:
    return f"{byte_count / 1_000_000:.1f} MB"
