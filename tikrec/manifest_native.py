"""Exclusive root-relative control staging with retained creation ownership."""

import ctypes as C
import os
from ctypes import wintypes as W
from pathlib import Path

from .attempt_scratch import ScratchHandle
from .capture_handoff_native import _ObjectAttributes, _UnicodeString, _IoStatusBlock
from .session_journal_types import ArtifactIdentity, require


def create_stage(parent, name, retain):
    """Allocate an exact FILE_CREATE owner before validation, never reopening a path."""
    require(parent.directory and parent.handle is not None and name == Path(name).name
            and ':' not in name and name.startswith('.tikrec-manifest-'), "invalid control staging name")
    owner = ScratchHandle.__new__(ScratchHandle)
    owner.api, owner.path, owner.handle, owner.fd = parent.api, parent.path / name, None, None
    owner.directory, owner.shared, owner.identity, owner.initial = False, False, None, None
    retain(owner)
    api = C.WinDLL("ntdll")
    api.NtCreateFile.argtypes = (C.POINTER(W.HANDLE), W.ULONG, C.POINTER(_ObjectAttributes),
        C.POINTER(_IoStatusBlock), C.c_void_p, W.ULONG, W.ULONG, W.ULONG, W.ULONG, C.c_void_p, W.ULONG)
    api.NtCreateFile.restype = W.LONG
    text = C.create_unicode_buffer(name)
    native_name = _UnicodeString(len(name) * 2, len(name) * 2 + 2, C.cast(text, W.LPWSTR))
    attrs = _ObjectAttributes(C.sizeof(_ObjectAttributes), parent.handle, C.pointer(native_name), 0x40, None, None)
    status, handle = _IoStatusBlock(), W.HANDLE()
    # READ/WRITE/DELETE/SYNCHRONIZE, FILE_CREATE, synchronous non-directory no-follow.
    result = api.NtCreateFile(C.byref(handle), 0xC0110000, C.byref(attrs), C.byref(status),
        None, 0x80, 1, 2, 0x200060, None, 0)
    if result < 0:
        api.RtlNtStatusToDosError.argtypes, api.RtlNtStatusToDosError.restype = (W.LONG,), W.ULONG
        raise C.WinError(api.RtlNtStatusToDosError(result))
    owner.handle = handle.value
    import msvcrt
    owner.fd = msvcrt.open_osfhandle(handle.value, os.O_BINARY | os.O_RDWR)
    info = owner._information()
    require(status.information == 2 and not info.attributes & 0x410 and info.links == 1,
            "control creation proof ambiguous")
    owner.identity, owner.initial = owner._path_identity(), owner.stamp
    require(owner.identity == ArtifactIdentity(parent.identity.volume, parent.identity.components + (name.casefold(),)), "control stage escaped parent")
    return owner


def write_stage(held, data):
    """Write a complete bounded document once, and require same-descriptor flush."""
    require(held.fd is not None and held.size == 0, "control staging not empty")
    view = memoryview(data)
    while view:
        count = os.write(held.fd, view)
        require(count > 0, "control staging short write")
        view = view[count:]
    held.flush()
    held.initial = held.stamp
