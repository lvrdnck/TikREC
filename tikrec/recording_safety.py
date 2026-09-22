"""Safe public recording inputs and bounded controller diagnostics."""

import re
from urllib.parse import urlsplit


def normalize_live_url(url: str) -> str:
    """Accept a public LIVE page and discard query/fragment metadata."""
    parsed = urlsplit(url)
    if (parsed.scheme not in {"http", "https"}
            or parsed.hostname not in {"tiktok.com", "www.tiktok.com"}
            or parsed.netloc not in {"tiktok.com", "www.tiktok.com"}
            or not re.fullmatch(r"/@[A-Za-z0-9_.]+/live/?", parsed.path)):
        raise ValueError("provide a public https://www.tiktok.com/@username/live URL")
    # Only the known public host reaches the resolver; callers cannot supply a CDN URL.
    return "https://www.tiktok.com" + parsed.path.rstrip("/")


def safe_error(error: BaseException) -> str:
    """Return a bounded single-line summary with ephemeral URLs removed."""
    return " ".join(re.sub(r"https?://\S+", "[URL redacted]", str(error)).split())[:500]
