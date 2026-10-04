"""Escaped callbacks and active source scopes cannot survive a sealed generation."""

from contextlib import nullcontext

import pytest

from tikrec.capture_fence import CaptureFence, FencedRaw
from tikrec.session_journal_types import JournalConflict, JournalError


def test_inflight_refusal_and_late_callback_does_not_mutate():
    fence = CaptureFence("session", 1, nullcontext)
    facts = []
    callback = fence.wrap(facts.append)
    with fence.operation():
        with pytest.raises(JournalError, match="in flight"):
            fence.close()
    callback("capturing")
    fence.close()
    with pytest.raises(JournalConflict):
        callback("replacement")
    assert facts == ["capturing"]


def test_iterator_closes_and_raw_methods_are_fenced():
    fence = CaptureFence("session", 2, nullcontext)
    closed = []
    def source():
        try:
            yield 1
        finally:
            closed.append(True)
    values = fence.iterator(source())
    assert next(values) == 1
    values.close()
    assert closed and fence.inflight == 0
    class Raw:
        write = observe_read_end = close = lambda *_: None
    raw = FencedRaw(Raw(), fence)
    fence.close()
    for callback in (raw.write, raw.observe_read_end, raw.close):
        with pytest.raises(JournalConflict):
            callback()
