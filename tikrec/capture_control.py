"""Cooperative capture cancellation without interrupting finalization."""

from collections.abc import Callable, Iterable, Iterator
from threading import Event

from .flv import FlvTag


class CaptureStopped(BaseException):
    """Unwind the writer through its normal close path on a requested stop."""


class CaptureControl:
    """Check a stop event at blocking-operation and complete-tag boundaries."""

    def __init__(self, event: Event | None, sleeper: Callable[[float], None]) -> None:
        self.event = event
        self.sleeper = sleeper

    def check(self) -> None:
        """Raise only during capture; the finalizer never receives this event."""
        if self.event is not None and self.event.is_set():
            raise CaptureStopped()

    def wait(self, seconds: float) -> None:
        """Make retry and offline-confirmation waits promptly cancellable."""
        self.check()
        if self.event is None:
            self.sleeper(seconds)
        else:
            self.event.wait(seconds)
        self.check()

    def resolve(self, resolver: Callable[[str], str], url: str) -> str:
        """Observe a stop even if a bounded resolver call ends with an error."""
        self.check()
        try:
            return resolver(url)
        finally:
            self.check()

    def tags(self, tags: Iterable[FlvTag]) -> Iterator[FlvTag]:
        """Stop between complete tags and close the underlying source iterator."""
        source = iter(tags)
        try:
            while True:
                self.check()
                try:
                    tag = next(source)
                except StopIteration:
                    self.check()
                    return
                finally:
                    # A stop during a blocked read takes precedence over read failure.
                    self.check()
                yield tag
        finally:
            close = getattr(source, "close", None)
            if close is not None:
                close()
