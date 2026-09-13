"""Offline boundary checks for cooperative cancellation."""

from threading import Event

import pytest

from tikrec.capture_control import CaptureControl, CaptureStopped
from tests.test_live import stream


def test_wait_uses_existing_sleeper_without_event():
    calls = []
    CaptureControl(None, calls.append).wait(2)
    assert calls == [2]


def test_set_event_cancels_wait_and_resolution():
    event = Event()
    event.set()
    control = CaptureControl(event, lambda _: pytest.fail("must not sleep"))
    with pytest.raises(CaptureStopped):
        control.wait(100)
    with pytest.raises(CaptureStopped):
        control.resolve(lambda _: pytest.fail("must not resolve"), "page")


def test_stop_during_read_closes_generator():
    event = Event()
    closed = []

    def source():
        try:
            yield stream()[0]
            event.set()
            raise OSError("read timed out")
        finally:
            closed.append(True)

    tags = CaptureControl(event, lambda _: None).tags(source())
    next(tags)
    with pytest.raises(CaptureStopped):
        next(tags)
    assert closed == [True]


def test_stop_during_resolution_overrides_offline_error():
    event = Event()

    def resolver(_):
        event.set()
        raise ValueError("offline")

    with pytest.raises(CaptureStopped):
        CaptureControl(event, lambda _: None).resolve(resolver, "page")
