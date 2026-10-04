"""Portable parameter and native layout contracts, with no process creation."""

import ctypes as C
import sys
from uuid import uuid4

import pytest

from tikrec.owned_process import OwnedProcess, _timeout
from tikrec.owned_process_api import Accounting, ExtendedLimits, ProcessInfo, Startup, StartupEx


@pytest.mark.parametrize("value", ["", "not-uuid", str(uuid4()).upper(), None, 123])
def test_session_and_attempt_require_explicit_canonical_uuid(value):
    with pytest.raises(ValueError):
        OwnedProcess(value, str(uuid4()))
    with pytest.raises(ValueError):
        OwnedProcess(str(uuid4()), value)


@pytest.mark.parametrize("value", [-1, 65537, True, None, 1.2])
def test_diagnostic_capacity_is_bounded(value):
    with pytest.raises(ValueError):
        OwnedProcess(str(uuid4()), str(uuid4()), diagnostic_limit=value)


@pytest.mark.parametrize("value", [-1, 31, float("nan"), float("inf"), True, None, "1"])
def test_wait_and_cleanup_timeouts_are_bounded(value):
    with pytest.raises(ValueError):
        _timeout(value)


@pytest.mark.skipif(sys.platform != "win32" or C.sizeof(C.c_void_p) != 8, reason="Windows x64 ABI")
def test_native_layout_matches_windows_x64():
    assert [C.sizeof(kind) for kind in (Startup, StartupEx, ProcessInfo, ExtendedLimits, Accounting)] == [104, 112, 24, 144, 48]


def test_not_created_cleanup_is_idempotent_without_loading_native_api():
    child = OwnedProcess(str(uuid4()), str(uuid4()))
    assert child.evidence().state == "not_created"
    assert child.close(0).state == "not_created" and child.native is None
    assert child.close(0).state == "not_created"
