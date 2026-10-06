"""Windows handle proofs for an explicit local capture-to-journal boundary."""

import ctypes
import os
from ctypes import wintypes
from pathlib import Path

from .retention_paths import local_path
from .session_journal_types import ArtifactIdentity, require


class _Information(ctypes.Structure):
    _fields_ = [("attributes", wintypes.DWORD), ("created", wintypes.FILETIME),
                ("accessed", wintypes.FILETIME), ("written", wintypes.FILETIME),
                ("volume", wintypes.DWORD), ("size_high", wintypes.DWORD),
                ("size_low", wintypes.DWORD), ("links", wintypes.DWORD),
                ("index_high", wintypes.DWORD), ("index_low", wintypes.DWORD)]


class _UnicodeString(ctypes.Structure):
    _fields_ = [("length", wintypes.USHORT), ("maximum", wintypes.USHORT),
                ("buffer", wintypes.LPWSTR)]


class _ObjectAttributes(ctypes.Structure):
    _fields_ = [("length", wintypes.ULONG), ("root", wintypes.HANDLE),
                ("name", ctypes.POINTER(_UnicodeString)), ("attributes", wintypes.ULONG),
                ("security", ctypes.c_void_p), ("quality", ctypes.c_void_p)]


class _IoStatusBlock(ctypes.Structure):
    _fields_ = [("status_or_pointer", ctypes.c_void_p), ("information", ctypes.c_size_t)]


def _kernel():
    require(os.name == "nt", "capture handoff requires native Windows proof")
    api = ctypes.WinDLL("kernel32", use_last_error=True)
    # Every pointer-sized handle signature is explicit on 64-bit Windows.
    api.CreateFileW.argtypes = (wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                               wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE)
    api.CreateFileW.restype = wintypes.HANDLE
    api.CloseHandle.argtypes = (wintypes.HANDLE,)
    api.CloseHandle.restype = wintypes.BOOL
    api.GetFileInformationByHandle.argtypes = (wintypes.HANDLE, ctypes.POINTER(_Information))
    api.GetFileInformationByHandle.restype = wintypes.BOOL
    api.GetFinalPathNameByHandleW.argtypes = (wintypes.HANDLE, wintypes.LPWSTR,
                                           wintypes.DWORD, wintypes.DWORD)
    api.GetFinalPathNameByHandleW.restype = wintypes.DWORD
    api.GetDriveTypeW.argtypes = (wintypes.LPCWSTR,)
    api.GetDriveTypeW.restype = wintypes.UINT
    return api


class NativeHandle:
    """Pin a no-follow native object; closed inputs deny all new data/delete access.

    Directory pins deny rename, but do not claim to prevent child creation. The
    bridge also owns the cooperative root lease and checks the complete inventory.
    Shared handles are only for directory/catalog lifetime, never a closure seal.
    """

    def __init__(self, path: Path, *, directory=False, shared=False, share_mode=None,
                 publication_right=False, read_only=False):
        self.api, self.path, self.fd, self.handle = _kernel(), Path(path), None, None
        self.ever_acquired = False
        self.directory, self.shared, self.read_only = directory, shared, read_only
        scope = local_path(self.path, directory=directory)
        require(self.api.GetDriveTypeW(scope.anchor) == 3, "handoff storage is not local fixed storage")
        # READ_ATTRIBUTES suffices for directory namespace pins. Closed files are
        # opened read/write with no sharing: existing readers/writers must unwind.
        require(type(read_only) is bool, "invalid native read mode")
        access = 0x80 if directory else 0x80000000 if shared or read_only else 0xC0000000
        # Only publication's original candidate acquisition requests DELETE.
        require(type(publication_right) is bool and (not publication_right or not directory and not shared),
                "invalid publication native access")
        if publication_right:
            access |= 0x10000
        sharing = (3 if directory or shared else 0) if share_mode is None else share_mode
        require(type(sharing) is int and 0 <= sharing <= 7, "invalid native sharing mode")
        handle = self.api.CreateFileW(str(scope), access, sharing,
                                      None, 3, 0x02200000, None)
        if handle == ctypes.c_void_p(-1).value:
            raise ctypes.WinError(ctypes.get_last_error())
        self.handle = handle
        self.ever_acquired = True
        try:
            information = self._information()
            require(not information.attributes & 0x400
                    and bool(information.attributes & 0x10) == directory,
                    "redirected or wrong native object")
            require(directory or information.links == 1, "multiply-linked capture evidence")
            self.identity = self._path_identity()
            if not directory:
                import msvcrt
                self.fd = msvcrt.open_osfhandle(handle, os.O_BINARY |
                    (os.O_RDONLY if shared or read_only else os.O_RDWR))
            self.initial = self.stamp
        except BaseException as original:
            try:
                self.close()
            except BaseException as cleanup:
                original.capture_cleanup_errors = [cleanup]
                original.capture_native_owners = [self]
                raise original from cleanup
            raise

    def __enter__(self):
        return self

    @classmethod
    def create_directory(cls, parent, name):
        """Create one child relative to a held parent and return its creation handle.

        NtCreateFile FILE_CREATE returns the exact handle atomically with directory
        creation; reopening by name after mkdir could silently adopt a replacement.
        """
        require(parent.directory and parent.handle is not None and name == Path(name).name
                and name.isascii() and name not in {"", ".", ".."}, "invalid relative scratch child")
        parent.verify()
        target = parent.path / name
        api = ctypes.WinDLL("ntdll", use_last_error=True)
        api.NtCreateFile.argtypes = (ctypes.POINTER(wintypes.HANDLE), wintypes.ULONG,
            ctypes.POINTER(_ObjectAttributes), ctypes.POINTER(_IoStatusBlock), ctypes.c_void_p,
            wintypes.ULONG, wintypes.ULONG, wintypes.ULONG, wintypes.ULONG, ctypes.c_void_p, wintypes.ULONG)
        api.NtCreateFile.restype = ctypes.c_long
        api.RtlNtStatusToDosError.argtypes = (ctypes.c_long,)
        api.RtlNtStatusToDosError.restype = wintypes.ULONG
        buffer = ctypes.create_unicode_buffer(name)
        native_name = _UnicodeString(len(name) * 2, len(name) * 2 + 2,
                                     ctypes.cast(buffer, wintypes.LPWSTR))
        attributes = _ObjectAttributes(ctypes.sizeof(_ObjectAttributes), parent.handle,
                                       ctypes.pointer(native_name), 0x40, None, None)
        status_block, handle = _IoStatusBlock(), wintypes.HANDLE()
        # FILE_CREATE is exclusive; the root-relative handle avoids path re-resolution.
        # DIRECTORY_FILE, synchronous I/O and OPEN_REPARSE_POINT refuse file/link substitution.
        status = api.NtCreateFile(ctypes.byref(handle), 0x100080, ctypes.byref(attributes),
            ctypes.byref(status_block), None, 0x10, 0, 2, 0x200021, None, 0)
        if status < 0:
            ctypes.set_last_error(api.RtlNtStatusToDosError(status))
            raise ctypes.WinError(ctypes.get_last_error())
        owner = cls.__new__(cls)
        owner.api, owner.path, owner.fd, owner.handle = parent.api, target, None, handle.value
        owner.ever_acquired = True
        owner.directory, owner.shared = True, False
        try:
            info = owner._information()
            require(status_block.information == 2 and not info.attributes & 0x400
                    and bool(info.attributes & 0x10), "scratch creation identity is ambiguous")
            owner.identity, owner.initial = owner._path_identity(), owner.stamp
            require(parent.identity.contains(owner.identity)
                    and owner.identity.components[-1] == name.casefold(),
                    "relative scratch creation escaped its parent")
            owner.verify()
            return owner
        except BaseException as error:
            # The successful native create remains reachable when proof fails.
            error.scratch_native_owner = owner
            error.scratch_native_created = True
            raise

    def __exit__(self, *_exc):
        try:
            self.close()
        except BaseException as cleanup:
            if len(_exc) > 1 and _exc[1] is not None:
                original = _exc[1]
                original.capture_cleanup_errors = [*getattr(original, "capture_cleanup_errors", []), cleanup]
                original.add_note("native evidence handle teardown also failed")
            else:
                raise

    @property
    def size(self):
        """Return size from the held object, never from a later path occupant."""
        info = self._information()
        return (info.size_high << 32) | info.size_low

    @property
    def stamp(self):
        """Bind native volume serial, file ID, length and last-write FILETIME."""
        info = self._information()
        index = (info.index_high << 32) | info.index_low
        written = (info.written.dwHighDateTime << 32) | info.written.dwLowDateTime
        return f"{info.volume:x}:{index:x}:{self.size:x}:{written:x}"

    def flush(self):
        """Require durable input flush through the same exclusively held descriptor."""
        require(self.fd is not None and not self.shared, "input is not exclusively held")
        os.fsync(self.fd)

    def read_control(self):
        """Read bounded control bytes through their held native file identity."""
        require(self.fd is not None and not self.shared and self.size <= 1024 * 1024,
                "control evidence is unavailable or too large")
        os.lseek(self.fd, 0, os.SEEK_SET)
        data = bytearray()
        while chunk := os.read(self.fd, 65536):
            data.extend(chunk)
            require(len(data) <= 1024 * 1024, "control evidence too large")
        return bytes(data)

    def verify(self):
        """Refuse identity/stamp drift while the protecting handle is still open."""
        stable = (self.stamp.split(":")[:2] == self.initial.split(":")[:2] if self.directory or self.shared
                  else self.stamp == self.initial)
        info = self._information()
        require(not info.attributes & 0x400 and (self.directory or info.links == 1),
                "held capture namespace became ambiguous")
        require(self._path_identity() == self.identity and stable,
                "held capture evidence changed")

    def close(self):
        """Release the exact native owner once, preserving errors for the caller."""
        if self.handle is not None:
            if self.fd is not None:
                os.close(self.fd)
                self.fd, self.handle = None, None
            elif not self.api.CloseHandle(self.handle):
                raise ctypes.WinError(ctypes.get_last_error())
            else:
                self.handle = None

    def _information(self):
        require(self.handle is not None, "native proof handle is closed")
        info = _Information()
        if not self.api.GetFileInformationByHandle(self.handle, ctypes.byref(info)):
            raise ctypes.WinError(ctypes.get_last_error())
        return info

    def _path_identity(self):
        buffer = ctypes.create_unicode_buffer(32768)
        # VOLUME_NAME_GUID obtains the volume identity from this handle, including
        # drive-letter aliases; FILE_NAME_NORMALIZED resolves native name casing.
        count = self.api.GetFinalPathNameByHandleW(self.handle, buffer, len(buffer), 1)
        require(0 < count < len(buffer), "native path identity unavailable")
        value = buffer.value.casefold()
        require(value.startswith("\\\\?\\volume{"), "native fixed-volume identity unavailable")
        volume, separator, tail = value[4:].partition("\\")
        require(separator and volume.endswith("}"), "invalid native volume identity")
        # A volume-root pin has no components; callers use a non-root disposable scope.
        return ArtifactIdentity(volume, tuple(tail.split("\\")))


def child_identity(parent: NativeHandle, name: str):
    """Prove existing native aliases, or reserve an absent basename in its pinned parent."""
    require(parent.directory and name == Path(name).name and name not in {"", ".", ".."})
    parent.verify()
    candidate = parent.path / name
    if candidate.exists() or candidate.is_symlink():
        # Existing 8.3/case aliases must resolve through the object, not its spelling.
        with NativeHandle(candidate, directory=candidate.is_dir(), shared=True) as held:
            require(parent.identity.contains(held.identity), "child native path escaped its parent")
            return held.identity
    return ArtifactIdentity(parent.identity.volume, parent.identity.components + (name.casefold(),))
