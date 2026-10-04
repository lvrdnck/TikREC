"""Independent exact-job test cleanup and native event barriers; no production access."""

import ctypes as C
import time
from uuid import uuid4

import pytest

from tikrec.owned_process import OwnedProcess
from tikrec.owned_process_api import Accounting, H, check, kernel


def duplicate(api, handle, *, source=None):
    """Retain an exact native object without granting children handle inheritance."""
    value = H()
    current = api.GetCurrentProcess()
    check(api.DuplicateHandle(source or current, handle, current, C.byref(value), 0, False, 2))
    return value.value


def stop_job(api, handle):
    """Independently terminate this disposable job and verify zero native members."""
    try:
        check(api.TerminateJobObject(handle, 99))
        deadline = time.monotonic() + 10
        while True:
            count = Accounting()
            check(api.QueryInformationJobObject(handle, 1, C.byref(count), C.sizeof(count), None))
            if count.active == 0:
                return
            assert time.monotonic() < deadline, "disposable job did not exit within independent cleanup bound"
            time.sleep(0.005)
    finally:
        check(api.CloseHandle(handle))


@pytest.fixture
def managed_process(monkeypatch):
    """Every test launch has a separate guard even if assertions/native probes fail."""
    api, owners, guards = kernel(), [], []
    def make(**options):
        owner = OwnedProcess(str(uuid4()), str(uuid4()), **options)
        owners.append(owner)
        def guard(boundary):
            if boundary == "after_create":
                guards.append(duplicate(api, owner.native.job))
        owner._fault = guard
        return owner
    yield make
    monkeypatch.undo()
    errors = []
    for guard in guards:
        try:
            stop_job(api, guard)
        except BaseException as error:
            errors.append(error)
    for owner in owners:
        owner._fault = lambda _: None
        try:
            if owner.closed and owner.native is not None and owner.native.process is not None:
                # A baseline lifecycle bug can hide controls behind closed=True.
                # The independent guard already proved exit; release exact handles.
                code, active = owner.native.status()
                assert code is not None and active == 0
                owner.native.close()
                continue
            assert owner.close(5).state in {"not_created", "confirmed_exited"}
        except BaseException as error:
            errors.append(error)
    assert not errors, repr(errors)


class Events:
    """Named manual-reset native barriers with bounded test waits."""

    def __init__(self):
        self.api, self.handles, self.names = kernel(), [], []
        self.api.CreateEventW.argtypes, self.api.CreateEventW.restype = [H, C.c_int, C.c_int, C.c_wchar_p], H
        self.api.SetEvent.argtypes, self.api.SetEvent.restype = [H], C.c_int
        for _ in range(2):
            name = "Local\\TikREC-test-" + str(uuid4())
            self.names.append(name)
            self.handles.append(check(self.api.CreateEventW(None, True, False, name)))

    def wait(self, index=0):
        """Wait for an actual child barrier, with a failure bound independent of the runner."""
        assert self.api.WaitForSingleObject(self.handles[index], 10000) == 0, "child barrier not reached"

    def release(self, index=1):
        """Permit the disposable child to advance its next deterministic boundary."""
        check(self.api.SetEvent(self.handles[index]))

    def __enter__(self):
        return self

    def __exit__(self, *_):
        for handle in self.handles:
            check(self.api.CloseHandle(handle))
