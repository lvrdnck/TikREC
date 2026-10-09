"""UUID/generation-bound callback lifetimes for the internal handoff path."""

from contextlib import contextmanager
from threading import RLock

from .session_journal_types import JournalConflict, require


class CaptureFence:
    """Track every in-flight source/control callback until a closed generation seals.

    The authority supplies the serialized fresh writer-opening check. A stored
    journal receipt is never used here as new writer permission.
    """

    def __init__(self, session_id, generation, opening, *, track_inputs=False):
        self.session_id, self.generation, self._opening = session_id, generation, opening
        self._lock, self.active, self.inflight = RLock(), True, 0
        self.cleanup_errors = []
        self.primary_error = None
        self.source_items = 0
        self.sources_opened, self.sources_closed, self.writer_openings = 0, 0, 0
        from .capture_input_owners import CaptureInputOwners
        self.inputs = CaptureInputOwners() if track_inputs else None
        from .capture_writer_owners import CaptureWriterOwners
        self.writers = CaptureWriterOwners(session_id, generation) if track_inputs else None

    def check(self):
        """Refuse callbacks after generation close, including after slot replacement."""
        with self._lock:
            if not self.active:
                raise JournalConflict("closed capture generation callback")

    @contextmanager
    def operation(self):
        """Hold a callback lifetime, permitting cooperative stop while sources wait."""
        with self._lock:
            self.check()
            self.inflight += 1
        try:
            yield
        finally:
            with self._lock:
                self.inflight -= 1

    def wrap(self, callback):
        """Bind a callback's entire execution to this capture generation."""
        if callback is None:
            return None
        def fenced(*args, **kwargs):
            with self.operation():
                return callback(*args, **kwargs)
        return fenced

    def iterator(self, source):
        """Fence iteration and source finally blocks without retaining a yielded scope."""
        iterator = iter(source)
        self.sources_opened += 1
        try:
            while True:
                with self.operation():
                    try:
                        value = next(iterator)
                        self.source_items += 1
                    except StopIteration:
                        return
                yield value
        finally:
            close = getattr(iterator, "close", None)
            if close is not None:
                import sys
                primary = sys.exc_info()[1]
                try:
                    self.wrap(close)()
                    self.sources_closed += 1
                except BaseException as cleanup:
                    self.cleanup_errors.append(cleanup)
                    if primary is not None and not isinstance(primary, GeneratorExit):
                        self.primary_error = primary
                        raise primary from cleanup
                    raise

    @contextmanager
    def opening(self):
        """Serialize fresh stop/admission checks with actual native writer opening."""
        with self.operation(), self._opening():
            yield

    @contextmanager
    def writer_opening(self):
        """Keep historical openings; a written failure additionally needs native lifetime proof."""
        with self.opening():
            self.writer_openings += 1
            yield

    def close(self):
        """Seal the callback lifetime only after every tracked operation unwound."""
        with self._lock:
            require(self.inflight == 0, "capture callbacks still in flight")
            self.active = False


class FencedRaw:
    """Preserve the real optional raw writer while fencing escaped method references."""

    def __init__(self, raw, fence):
        self.raw = raw
        for name in ("write", "observe_read_end", "close"):
            setattr(self, name, fence.wrap(getattr(raw, name)))

    def __getattr__(self, name):
        return getattr(self.raw, name)


def capture_callback(callback, fence):
    """Use existing synchronous callbacks unchanged unless the internal fence is supplied."""
    return callback if fence is None else fence.wrap(callback)


def live_callbacks(fence, *callbacks):
    """Bind the LIVE observer set to an internal generation when supplied."""
    return tuple(capture_callback(callback, fence) for callback in callbacks)


def close_connection_sources(controlled, tags, raw, fence):
    """Preserve the synchronous default and collect internal closure failures."""
    if fence is not None:
        return unwind_sources(controlled, tags, raw, fence)
    controlled.close()
    close = getattr(tags, "close", None)
    if close is not None:
        close()
    if raw is not None:
        raw.close()


def unwind_sources(controlled, tags, raw, fence):
    """Attempt every close and keep original failure plus secondary closure evidence."""
    import sys
    primary = sys.exc_info()[1]
    errors = []
    for value in (controlled, tags, raw):
        close = getattr(value, "close", None)
        if close is not None:
            try:
                close()
            except BaseException as error:
                errors.append(error)
    if fence is not None:
        fence.cleanup_errors.extend(errors)
    if errors:
        if primary is not None:
            if fence is not None:
                fence.primary_error = primary
            primary.add_note("capture source cleanup also failed; responsibility retained")
        else:
            raise errors[0]
