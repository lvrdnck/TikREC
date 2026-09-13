"""Observe capture milestones without changing source or writer decisions."""

from __future__ import annotations

import time
from collections.abc import Callable, Iterable, Iterator

from .flv import FlvTag


class ConnectionObservation:
    """Wall-clock processing milestones and the resolver's selected rendition.

    The observation clock is independent of the existing policy clock so an
    injected policy clock keeps the same call sequence as before instrumentation.
    """

    def __init__(self, clock: Callable[[], float] = time.time) -> None:
        self.clock = clock
        self.resolved_at: float | None = None
        self.http_opened_at: float | None = None
        self.first_media_tag_at: float | None = None
        self.first_retained_media_at: float | None = None
        self.last_retained_media_at: float | None = None
        self.rendition_label: str | None = None
        self.rendition_source: str | None = None

    def resolved(self, url: str) -> None:
        """Record successful resolution, preserving plain-string custom resolvers."""
        self.resolved_at = self.clock()
        self.rendition_label = getattr(url, "rendition_label", None)
        self.rendition_source = getattr(url, "rendition_source", None)

    def opened(self) -> None:
        """Record when the HTTP response has opened, before reading its body."""
        self.http_opened_at = self.clock()

    def tags(self, tags: Iterable[FlvTag]) -> Iterator[FlvTag]:
        """Observe the first parsed media tag, including media the gate rejects."""
        for tag in tags:
            if tag.is_media and self.first_media_tag_at is None:
                self.first_media_tag_at = self.clock()
            yield tag

    def retained(self) -> None:
        """Observe a successfully written media tag, excluding sequence headers."""
        now = self.clock()
        if self.first_retained_media_at is None:
            self.first_retained_media_at = now
        self.last_retained_media_at = now

    def values(self) -> dict[str, float | str | None]:
        """Return the optional evidence fields stored in a connection record."""
        return {name: getattr(self, name) for name in (
            "resolved_at", "http_opened_at", "first_media_tag_at",
            "first_retained_media_at", "last_retained_media_at",
            "rendition_label", "rendition_source",
        )}
