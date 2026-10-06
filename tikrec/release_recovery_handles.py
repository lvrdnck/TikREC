"""Exact Windows open-object references for recovery cleanup, never path adoption."""

import ctypes
import os
from contextlib import contextmanager
from contextvars import ContextVar
from ctypes import wintypes

from .session_journal_types import require


_scope = ContextVar('release_recovery_cleanup_scope', default=None)


@contextmanager
def cleanup_scope(owner):
    """Register partial lifecycle descriptors before validation can fail."""
    token = _scope.set(owner)
    try:
        yield
    finally:
        _scope.reset(token)


def guard_descriptor(descriptor):
    """Protect only a fresh descriptor acquired by the current recovery."""
    owner = _scope.get()
    if owner is None:
        return None
    import msvcrt
    return NativeCloseGuard(owner, msvcrt.get_osfhandle(descriptor), descriptor)


class NativeCloseGuard:
    """Keep an exact kernel object reference across CRT close failures and reuse."""

    def __init__(self, owner, original, descriptor=None, *, resource_key='lease'):
        self.original, self.descriptor, self.handle = original, descriptor, None
        self.resource_key, self.attempts = resource_key, 0
        self.api = ctypes.WinDLL('kernel32', use_last_error=True)
        self.api.GetCurrentProcess.restype = wintypes.HANDLE
        self.api.DuplicateHandle.argtypes = (wintypes.HANDLE, wintypes.HANDLE, wintypes.HANDLE,
            ctypes.POINTER(wintypes.HANDLE), wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
        self.api.DuplicateHandle.restype = wintypes.BOOL
        self.compare = ctypes.WinDLL('kernelbase', use_last_error=True).CompareObjectHandles
        self.compare.argtypes = (wintypes.HANDLE, wintypes.HANDLE)
        self.compare.restype = wintypes.BOOL
        self.api.CloseHandle.argtypes = (wintypes.HANDLE,)
        self.api.CloseHandle.restype = wintypes.BOOL
        owner.native_close_guards.append(self)
        duplicate = wintypes.HANDLE()
        process = self.api.GetCurrentProcess()
        if not self.api.DuplicateHandle(process, original, process, ctypes.byref(duplicate), 0, False, 2):
            raise ctypes.WinError(ctypes.get_last_error())
        self.handle = duplicate.value

    @property
    def retained(self):
        """A duplicate reference is ownership even after the CRT stream says closed."""
        return self.original is not None or self.handle is not None

    def _same(self, handle):
        require(self.handle is not None, 'native close reference was not acquired')
        ctypes.set_last_error(0)
        if self.compare(handle, self.handle):
            return True
        error = ctypes.get_last_error()
        require(error in (6, 1656), 'native close identity is uncertain')
        return False

    def _descriptor_live(self):
        if self.descriptor is None:
            return False
        import msvcrt
        try:
            handle = msvcrt.get_osfhandle(self.descriptor)
        except OSError:
            return False
        require(self._same(handle), 'retained lifecycle descriptor identity is uncertain')
        return True

    def _finish(self):
        if self.original is not None:
            require(not self._same(self.original), 'native close left its original handle live')
            self.original = None
        if self.handle is not None:
            if not self.api.CloseHandle(self.handle):
                raise ctypes.WinError(ctypes.get_last_error())
            self.handle = None

    def close(self, callback=None):
        """Close only this open object; never a reused CRT or Windows identifier."""
        if not self.retained:
            return
        self.attempts += 1
        self._descriptor_live()  # Refuse a reused CRT number before any close.
        if self.original is not None and self._same(self.original):
            try:
                if callback is not None and (self.descriptor is None or self._descriptor_live()):
                    callback()
                elif self._descriptor_live():
                    os.close(self.descriptor)
                elif not self.api.CloseHandle(self.original):
                    raise ctypes.WinError(ctypes.get_last_error())
            except BaseException as original:
                # A reported error can follow a successful close. Keep its identity.
                if not self._same(self.original):
                    try:
                        self._finish()
                    except BaseException as secondary:
                        original.capture_cleanup_errors = [secondary]
                raise
        self._finish()

    def close_retired_reference(self):
        """Retire an orphaned duplicate only after its original is demonstrably gone."""
        if self.retained and self.handle is not None and (self.original is None or not self._same(self.original)):
            self.attempts += 1
            self._finish()

    def stream(self, raw):
        """Bind the stream to the original native reference captured before fdopen."""
        return GuardedStream(raw, self)


class GuardedStream:
    """Delegate lease I/O while separately proving native close."""

    def __init__(self, raw, guard):
        self.raw, self.guard = raw, guard

    def __getattr__(self, name):
        return getattr(self.raw, name)

    def close(self):
        """Retry a live native handle even when Python already marked it closed."""
        self.guard.close(None if self.raw.closed else self.raw.close)
