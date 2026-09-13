"""Format live progress and validate the existing reconnect policy."""

from __future__ import annotations

import re
from collections.abc import Callable

from .writer import TimestampReplay

_URL_PATTERN = re.compile(r"https?://\S+")


def _report(progress: Callable[[str], None] | None, message: str) -> None:
    if progress is not None:
        progress(message)


def _warn(
    warning: Callable[[str], None] | None,
    progress: Callable[[str], None] | None,
    message: str,
) -> None:
    if warning is not None:
        warning(message)
    else:
        _report(progress, f"warning: {message}")


def _safe_reason(error: Exception) -> str:
    return _URL_PATTERN.sub("[URL redacted]", str(error))


def _timestamp_replay_message(replay: TimestampReplay) -> str:
    suffix = "recovery" if replay.recovered else "part end"
    return (
        f"warning: timestamp replay detected; {replay.path.name} tag {replay.position} "
        f"jumped back {replay.magnitude}ms; {replay.replayed_tag_count} tags replayed "
        f"before {suffix}; this part may not validate"
    )


def _next_failure_counts(media: bool, failures: int, empty: int) -> tuple[int, int]:
    """Reset both connection streaks when a failed read still retained media."""
    return (0, 0) if media else (failures + 1, empty)


def _validate_limits(failures: int, empty: int, backoff: float, offline_checks: int, offline_interval: float) -> None:
    if not isinstance(failures, int) or failures < 1:
        raise ValueError("max_consecutive_failures must be a positive integer")
    if not isinstance(empty, int) or empty < 1:
        raise ValueError("max_consecutive_empty_connections must be a positive integer")
    if backoff < 0:
        raise ValueError("backoff_seconds must not be negative")
    if not isinstance(offline_checks, int) or offline_checks < 1:
        raise ValueError("offline_confirmation_checks must be a positive integer")
    if offline_interval < 0:
        raise ValueError("offline_confirmation_interval must not be negative")
