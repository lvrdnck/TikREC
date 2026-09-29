"""Windows removal through an exclusive, verified filesystem-object handle."""

from __future__ import annotations

import ctypes
import hashlib
import os
from ctypes import wintypes


_READ_AND_DELETE = 0x80010000  # GENERIC_READ | DELETE.
_OPEN_EXISTING = 3
_OPEN_NOFOLLOW = 0x02200000  # BACKUP_SEMANTICS (directories) | OPEN_REPARSE_POINT.

class _RenameInfo(ctypes.Structure):
    _fields_ = [("replace", ctypes.c_ubyte), ("root", wintypes.HANDLE),
                ("length", wintypes.DWORD), ("name", wintypes.WCHAR * 1)]


def _kernel():
    library = ctypes.WinDLL("kernel32", use_last_error=True)
    # Explicit pointer-sized signatures prevent ctypes' default int truncation.
    library.CreateFileW.argtypes = (wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                   wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD,
                                   wintypes.HANDLE)
    library.CreateFileW.restype = wintypes.HANDLE
    library.SetFileInformationByHandle.argtypes = (
        wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID, wintypes.DWORD)
    library.SetFileInformationByHandle.restype = wintypes.BOOL
    library.CloseHandle.argtypes = (wintypes.HANDLE,)
    library.CloseHandle.restype = wintypes.BOOL
    return library


class HeldArtifact:
    """Deny concurrent data access and namespace replacement until exact deletion."""

    def __init__(self, path, expected) -> None:
        self.path, self.expected = path, expected
        self.fd = None
        # Entry cleanup can fail before the with body starts; retain it separately.
        self.enter_cleanup_error: BaseException | None = None
        self.api = _kernel()

    def __enter__(self):
        import msvcrt

        # DELETE + GENERIC_READ, no sharing: existing writers/readers refuse the
        # open, and new data/delete handles cannot substitute the held object.
        # OPEN_REPARSE_POINT opens the final link itself for rejection below.
        handle = self.api.CreateFileW(str(self.path), _READ_AND_DELETE, 0, None,
                                      _OPEN_EXISTING, _OPEN_NOFOLLOW, None)
        if handle == ctypes.c_void_p(-1).value:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            self.fd = msvcrt.open_osfhandle(handle, os.O_RDONLY | os.O_BINARY)
        except BaseException as error:
            try:
                self.api.CloseHandle(handle)
            except BaseException as cleanup:
                self.enter_cleanup_error = cleanup
                raise error from cleanup
            raise
        try:
            self._identity()
        except BaseException as error:
            try:
                self.close()
            except BaseException as cleanup:
                self.enter_cleanup_error = cleanup
                raise error from cleanup
            raise
        return self

    def __exit__(self, *_exc) -> None:
        self.close()

    def close(self) -> None:
        """Close the owning CRT descriptor once, including on failed proof."""
        if self.fd is not None:
            descriptor, self.fd = self.fd, None
            os.close(descriptor)

    def rename(self, destination) -> None:
        """Atomically rename this object, refusing any occupied destination."""
        name = str(destination).encode("utf-16-le")
        # Win32 needs a terminating WCHAR in the buffer, though length excludes it.
        buffer = ctypes.create_string_buffer(_RenameInfo.name.offset + len(name) + 2)
        info = _RenameInfo.from_buffer(buffer)
        info.replace, info.length = 0, len(name)
        ctypes.memmove(ctypes.addressof(buffer) + _RenameInfo.name.offset, name, len(name))
        self._set(3, buffer, len(buffer))  # FileRenameInfo, ReplaceIfExists=FALSE.
        self.path = destination

    def prove(self, digest: str | None) -> None:
        """Verify held identity and hash file bytes through that same handle."""
        before = self._identity()
        if self.expected.kind == "directory":
            return  # FileDispositionInfo itself refuses a nonempty directory.
        if digest is None:
            raise ValueError("retention held file has no byte proof")
        os.lseek(self.fd, 0, os.SEEK_SET)
        actual, count = hashlib.sha256(), 0
        while chunk := os.read(self.fd, 64 * 1024):
            actual.update(chunk)
            count += len(chunk)
        if (self._identity() != before or count != self.expected.size
                or actual.hexdigest() != digest):
            raise ValueError("retention held artifact byte proof changed")

    def delete(self) -> None:
        """Mark this exact file or empty directory for deletion and close it."""
        self._identity()
        flag = ctypes.c_ubyte(1)
        self._set(4, ctypes.byref(flag), 1)  # FileDispositionInfo targets the handle.
        # Exclusive sharing makes this the last data/delete handle. No pathname
        # unlink follows, so a later name occupant can never be removed here.
        self.close()

    def _set(self, kind, buffer, size):
        import msvcrt

        if self.fd is None:
            raise ValueError("retention artifact handle is closed")
        if not self.api.SetFileInformationByHandle(
                msvcrt.get_osfhandle(self.fd), kind, buffer, size):
            raise ctypes.WinError(ctypes.get_last_error())

    def _identity(self):
        if self.fd is None:
            raise ValueError("retention artifact handle is closed")
        held, item = os.fstat(self.fd), self.expected
        common = (held.st_mode, held.st_dev, held.st_ino, held.st_nlink,
                  getattr(held, "st_file_attributes", 0))
        expected = (item.mode, item.device, item.inode, item.link_count, item.attributes)
        # Windows path/handle ctime are incomparable; rename also changes ctime.
        # Directories legitimately changed timestamps while their children went.
        if (common != expected or common[-1] & 0x400 or item.kind == "file"
                and (held.st_size, held.st_mtime_ns) != (item.size, item.mtime_ns)):
            raise ValueError("retention held artifact identity changed")
        return common + (held.st_size, held.st_mtime_ns, held.st_ctime_ns)
