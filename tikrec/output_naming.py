"""Safe local recording paths for explicit and automatically named outputs."""

from __future__ import annotations

import re
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote, urlsplit

from .configuration import (
    ConfigurationError,
    ConfigurationStore,
    default_config_path,
    resolve_recording_output,
)
from .creator_identity import CreatorIdentityError, validate_creator_handle
from .tiktok import TikTokResolutionError, _validate_live_page_url


_UNSAFE_FILENAME = re.compile(r"[^A-Za-z0-9._-]+")
_REPEATED_SEPARATOR = re.compile(r"[-_.]{2,}")
_MAX_COLLISION_INDEX = 1000


class OutputNameUnavailableError(ConfigurationError):
    """The bounded automatic-name search found no unoccupied candidate."""


class OutputPathInspectionError(ConfigurationError):
    """Automatic naming could not safely determine whether a path is occupied."""


def local_recording_paths(
    command: str,
    url: str,
    output: str | None,
    *,
    config_path: str | None = None,
    clock: Callable[[], datetime] | None = None,
) -> tuple[Path, Path]:
    """Resolve explicit output precedence or safely name one local LIVE recording."""
    if output is not None:
        output_path = Path(output)
        if not output_path.is_absolute():
            store = ConfigurationStore(
                Path(config_path) if config_path else default_config_path()
            )
            output_path = resolve_recording_output(output_path, store.load())
        return output_path, _parts_path(output_path)
    if command != "live":
        raise ConfigurationError("--output is required for this command")

    store = ConfigurationStore(Path(config_path) if config_path else default_config_path())
    configuration = store.load()
    if configuration.output_directory is None:
        raise ConfigurationError(
            "automatic LIVE naming requires configured output_directory; "
            "run 'tikrec config set output-directory DIRECTORY' or provide --output"
        )
    handle = safe_creator_handle(url)
    moment = (clock or datetime.now)()
    return _available_paths(
        configuration.output_directory, f"{handle}-{_timestamp(moment)}"
    )


def monitored_recording_paths(
    directory: Path, creator: str, *, moment: datetime
) -> tuple[Path, Path]:
    """Allocate a non-mutating automatic candidate for one canonical creator."""
    try:
        creator = validate_creator_handle(creator)
    except CreatorIdentityError as error:
        raise ConfigurationError(str(error)) from None
    return _available_paths(directory, f"{creator}-{_timestamp(moment)}")


def safe_creator_handle(url: str) -> str:
    """Extract and conservatively sanitize only the public LIVE creator segment."""
    try:
        parsed = urlsplit(url)
        segments = [segment for segment in parsed.path.split("/") if segment]
        if (len(segments) != 2 or parsed.username is not None
                or parsed.password is not None or parsed.port is not None):
            raise ValueError("nonstandard LIVE URL")
        encoded_handle = _validate_live_page_url(url)
        if re.search(r"%(?![0-9A-Fa-f]{2})", encoded_handle):
            raise ValueError("malformed percent escape")
        raw_handle = unquote(encoded_handle, errors="strict")
    except (UnicodeError, TikTokResolutionError, ValueError):
        raise ConfigurationError(
            "automatic LIVE naming requires a standard public TikTok creator LIVE URL"
        ) from None
    # Replace every non-portable run rather than allowing URL text to become a path.
    handle = _UNSAFE_FILENAME.sub("-", raw_handle)
    handle = _REPEATED_SEPARATOR.sub("-", handle).strip(" .-_")
    if not handle or handle in {".", ".."}:
        raise ConfigurationError(
            "automatic LIVE naming could not extract a safe creator handle"
        )
    # TikTok handles are short; the bound also keeps manually unusual URLs manageable.
    return handle[:64].rstrip(" .-_")


def _available_paths(directory: Path, stem: str) -> tuple[Path, Path]:
    base = directory.resolve(strict=False)
    for index in range(1, _MAX_COLLISION_INDEX + 1):
        suffix = "" if index == 1 else f"-{index}"
        output = base / f"{stem}{suffix}.mp4"
        parts = _parts_path(output)
        # Direct construction plus this assertion keeps future refactors inside the base.
        if output.parent != base or parts.parent != base:
            raise ConfigurationError("automatic recording path escaped output_directory")
        if not _occupied(output) and not _occupied(parts):
            return output, parts
    raise OutputNameUnavailableError(
        "could not find an unused automatic LIVE output name"
    )


def _parts_path(output: Path) -> Path:
    return output.with_name(f"{output.stem}.parts")


def _occupied(path: Path) -> bool:
    try:
        # lstat treats regular files, directories, and broken symlinks as occupied.
        path.lstat()
    except FileNotFoundError:
        return False
    except OSError:
        raise OutputPathInspectionError(
            "could not inspect automatic recording path"
        ) from None
    return True


def _timestamp(moment: datetime) -> str:
    return (
        f"{moment.year:04d}{moment.month:02d}{moment.day:02d}-"
        f"{moment.hour:02d}{moment.minute:02d}{moment.second:02d}"
    )
