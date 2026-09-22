"""Offline normalization and validation for configured public creator handles."""

from __future__ import annotations

import re
from urllib.parse import urlsplit


_HANDLE = re.compile(r"[a-z0-9_](?:[a-z0-9._]{0,22}[a-z0-9_])?")
_CREATOR_HELP = (
    "creator must be a 1-24 character TikTok handle using letters, numbers, "
    "underscores, or internal periods"
)


class CreatorIdentityError(ValueError):
    """A creator value is malformed or not safe to persist."""


def normalize_creator(value: str) -> str:
    """Normalize one bare, @-prefixed, or standard public LIVE creator value."""
    if not isinstance(value, str):
        raise CreatorIdentityError(_CREATOR_HELP)
    candidate = value.strip()
    if candidate.startswith("https://"):
        candidate = _handle_from_live_url(candidate)
    elif candidate.startswith("@"):
        candidate = candidate[1:]
    elif "://" in candidate:
        raise CreatorIdentityError(
            "creator URL must use https://www.tiktok.com/@handle/live"
        )
    canonical = candidate.lower()
    validate_creator_handle(canonical)
    return canonical


def validate_creator_handle(value: object) -> str:
    """Return one already-canonical handle or reject unsafe persisted identity."""
    if type(value) is not str or value != value.lower() or not _HANDLE.fullmatch(value):
        raise CreatorIdentityError(_CREATOR_HELP)
    return value


def validate_monitored_creators(value: object) -> tuple[str, ...]:
    """Validate the ordered, duplicate-free creator tuple stored in configuration."""
    if type(value) is not tuple:
        raise CreatorIdentityError("monitored_creators must be an ordered list")
    creators = tuple(validate_creator_handle(handle) for handle in value)
    if len(creators) != len(set(creators)):
        raise CreatorIdentityError("monitored_creators must not contain duplicates")
    return creators


def _handle_from_live_url(value: str) -> str:
    try:
        parsed = urlsplit(value)
        segments = parsed.path.split("/")
        valid = (
            parsed.scheme == "https"
            and parsed.hostname == "www.tiktok.com"
            and parsed.username is None
            and parsed.password is None
            and parsed.port is None
            and len(segments) == 3
            and segments[0] == ""
            and segments[1].startswith("@")
            and segments[2].lower() == "live"
        )
    except ValueError:
        valid = False
    if not valid:
        raise CreatorIdentityError(
            "creator URL must use https://www.tiktok.com/@handle/live"
        )
    return segments[1][1:]
