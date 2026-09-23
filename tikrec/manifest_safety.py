"""Bound error text persisted in session manifests."""

import re


_URL_PATTERN = re.compile(r"https?://\S+")


def safe_reason(error: BaseException | str | None) -> str | None:
    """Redact transport URLs from durable session errors."""
    return None if error is None else _URL_PATTERN.sub("[URL redacted]", str(error))
