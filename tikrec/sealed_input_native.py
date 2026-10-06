"""Read-compatible Windows pins, separate from capture's zero-sharing closure."""

import ctypes
from ctypes import wintypes
from pathlib import Path

from .capture_handoff_native import NativeHandle, _kernel
from .retention_paths import local_path
from .session_journal_types import require


class ReadProtection(NativeHandle):
    """Retain an exact noninheritable handle until native close confirms release.

    Files permit readers but deny data-write/delete sharing. Namespace/lock pins
    permit writers and deny deletion; they never claim to prevent new children.
    Allocate this owner before calling open so even acquisition faults retain it.
    """

    def __init__(self, path, *, directory=False, namespace=False, control_right=False):
        self.path, self.directory, self.namespace = Path(path), directory, namespace
        require(type(control_right) is bool and (not control_right or
            not directory and not namespace and self.path.name == "session.json"), "invalid control rights")
        # Only the completion-capable original manifest receives DELETE; its
        # bytes remain read-only, and every other input/default keeps prior rights.
        self.control_right = control_right
        self.api, self.handle, self.fd = _kernel(), None, None
        self.initial, self.identity = None, None

    def open(self):
        """Open existing local evidence without following redirects or owning a CRT fd."""
        scope = local_path(self.path, directory=self.directory)
        require(self.api.GetDriveTypeW(scope.anchor) == 3, "read guard requires fixed local storage")
        # NULL security attributes disable inheritance. Only ordinary input readers
        # share data access; parent/lock pins also permit cooperative data writers.
        namespace = self.directory or self.namespace
        handle = self.api.CreateFileW(str(scope), 0x80 if namespace else 0x80000000 | (0x10000 if self.control_right else 0),
                                      3 if namespace else 1, None, 3, 0x02200000, None)
        if handle == ctypes.c_void_p(-1).value:
            raise ctypes.WinError(ctypes.get_last_error())
        self.handle = handle
        info = self._information()
        require(not info.attributes & 0x400 and bool(info.attributes & 0x10) == self.directory
                and (self.directory or info.links == 1), "ambiguous sealed native object")
        self.identity, self.initial = self._path_identity(), self.stamp
        return self

    def verify(self):
        """Check held metadata and the addressed native path without replacing protection."""
        local_path(self.path, directory=self.directory)
        info = self._information()
        require(not info.attributes & 0x400 and (self.directory or info.links == 1),
                "sealed namespace became ambiguous")
        stable = (self.stamp.split(":")[:2] == self.initial.split(":")[:2]
                  if self.directory else self.stamp == self.initial)
        require(stable and self._path_identity() == self.identity, "sealed object changed")

    def read_control(self):
        """Read at most 1 MiB from the held native object with bounded synchronous reads."""
        require(not self.directory and not self.namespace and self.size <= 1024 * 1024,
                "sealed control unavailable or too large")
        api = self.api
        api.SetFilePointerEx.argtypes = (wintypes.HANDLE, ctypes.c_longlong, ctypes.c_void_p, wintypes.DWORD)
        api.SetFilePointerEx.restype = wintypes.BOOL
        api.ReadFile.argtypes = (wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD,
                                ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p)
        api.ReadFile.restype = wintypes.BOOL
        if not api.SetFilePointerEx(self.handle, 0, None, 0):
            raise ctypes.WinError(ctypes.get_last_error())
        data = bytearray()
        # Seventeen fixed-size reads include the EOF proof at the maximum size.
        for _ in range(17):
            buffer, count = ctypes.create_string_buffer(65536), wintypes.DWORD()
            if not api.ReadFile(self.handle, buffer, len(buffer), ctypes.byref(count), None):
                raise ctypes.WinError(ctypes.get_last_error())
            if not count.value:
                return bytes(data)
            data.extend(buffer.raw[:count.value])
            require(len(data) <= 1024 * 1024, "sealed control too large")
        raise ValueError("sealed control EOF not proved")

    def close(self):
        """Clear ownership only after exact native CloseHandle succeeds."""
        if self.handle is not None:
            if not self.api.CloseHandle(self.handle):
                raise ctypes.WinError(ctypes.get_last_error())
            self.handle = None
