"""Exact retained-handle no-replace rename, with no pathname reopen or fallback."""

import ctypes as C
from ctypes import wintypes as W
from pathlib import Path

from .session_journal_types import require


class _Rename(C.Structure):
    _fields_ = [("replace", W.BOOLEAN), ("root", W.HANDLE),
                ("length", W.DWORD), ("name", W.WCHAR * 1)]


class _Status(C.Structure):
    _fields_ = [("status", C.c_void_p), ("information", C.c_size_t)]


def rename_no_replace(held, parent, name):
    """Rename one retained DELETE-capable file relative to the pinned parent."""
    require(held.handle is not None and parent.handle is not None and parent.directory
            and held.identity.volume == parent.identity.volume
            and name == Path(name).name and ':' not in name and name not in {'', '.', '..'},
            "unsupported native publication namespace")
    # NtSetInformationFile supports a real RootDirectory, avoiding path-parent
    # resolution during the operation. ReplaceIfExists stays FALSE.
    encoded = name.encode("utf-16-le")
    buffer = C.create_string_buffer(_Rename.name.offset + len(encoded))
    header = C.cast(buffer, C.POINTER(_Rename)).contents
    header.replace, header.root, header.length = False, parent.handle, len(encoded)
    C.memmove(C.addressof(buffer) + _Rename.name.offset, encoded, len(encoded))
    api = C.WinDLL("ntdll")
    api.NtSetInformationFile.argtypes = (W.HANDLE, C.POINTER(_Status), C.c_void_p, W.ULONG, W.ULONG)
    api.NtSetInformationFile.restype = W.LONG
    status = _Status()
    result = api.NtSetInformationFile(held.handle, C.byref(status), buffer, len(buffer), 10)
    if result < 0:
        api.RtlNtStatusToDosError.argtypes = (W.LONG,)
        api.RtlNtStatusToDosError.restype = W.ULONG
        raise C.WinError(api.RtlNtStatusToDosError(result))
