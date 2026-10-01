"""One service gate spanning acceptance, writers, policy and retention proof."""

from contextlib import contextmanager
from threading import RLock, get_ident


class MutationGate:
    """Exclude new trusted mutation work without stopping existing recordings."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._writers = 0
        self._exclusive = None

    @contextmanager
    def writer(self):
        """Reserve mutation before starting work, including pending worker acceptance."""
        with self._lock:
            if self._exclusive is not None:
                raise ValueError("managed storage is busy with retention")
            self._writers += 1
        try:
            yield
        finally:
            with self._lock:
                self._writers -= 1

    @contextmanager
    def exclusive(self):
        """Refuse occupied storage and hold exclusion through proof and cleanup."""
        with self._lock:
            if self._exclusive is not None or self._writers:
                raise ValueError("managed storage has active mutation work")
            self._exclusive = get_ident()
        try:
            yield
        finally:
            with self._lock:
                self._exclusive = None

    def assert_exclusive(self) -> None:
        """Require this thread to own the entire destructive proof/removal interval."""
        with self._lock:
            if self._exclusive != get_ident() or self._writers:
                raise ValueError("managed retention authority is not held")
