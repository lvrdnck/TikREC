"""Read-only Linux mount evidence bound to no-follow open descriptors."""

from __future__ import annotations

import ctypes
import os
import stat
from dataclasses import dataclass
from pathlib import Path


BTRFS_SUPER_MAGIC = 0x9123683E


@dataclass(frozen=True)
class LinuxPathEvidence:
    """Kernel mount, subvolume device, and filesystem type for one held path."""

    mount_id: str
    device: tuple[int, int]
    filesystem_type: int


def read_mountinfo() -> str:
    """Read bounded namespace evidence without silently truncating it."""
    with Path("/proc/self/mountinfo").open(encoding="utf-8") as handle:
        value = handle.read(1_000_001)
    if len(value) > 1_000_000:
        raise ValueError("retention mount table exceeds evidence limit")
    return value


def linux_path_evidence(path: Path, mountinfo: str) -> LinuxPathEvidence | None:
    """Refuse redirection or observed path/mount replacement during inspection.

    O_PATH pins identities without reading files or opening devices for I/O.
    This is a read-only observation, never an exclusive mutation guarantee.
    """
    descriptors = []
    try:
        if not path.is_absolute() or ".." in path.parts or read_mountinfo() != mountinfo:
            return None
        flags = os.O_PATH | os.O_NOFOLLOW | os.O_CLOEXEC
        descriptor = os.open("/", flags | os.O_DIRECTORY)
        descriptors.append((Path("/"), descriptor))
        for index, name in enumerate(path.parts[1:]):
            # Each parent is held; an intermediate symlink must never be followed.
            options = flags | (os.O_DIRECTORY if index < len(path.parts) - 2 else 0)
            descriptor = os.open(name, options, dir_fd=descriptor)
            descriptors.append((descriptors[-1][0] / name, descriptor))
        details = os.fstat(descriptor)
        if not (stat.S_ISDIR(details.st_mode) or stat.S_ISREG(details.st_mode)):
            return None
        mount_id = descriptor_mount_id(descriptor)
        filesystem_type = descriptor_filesystem_type(descriptor)
        for component, held in descriptors:
            current, expected = component.lstat(), os.fstat(held)
            if ((current.st_dev, current.st_ino, current.st_mode)
                    != (expected.st_dev, expected.st_ino, expected.st_mode)):
                return None
        if read_mountinfo() != mountinfo or descriptor_mount_id(descriptor) != mount_id:
            return None
        return LinuxPathEvidence(mount_id, (os.major(details.st_dev),
                                           os.minor(details.st_dev)), filesystem_type)
    except (OSError, ValueError, AttributeError, OverflowError):
        return None
    finally:
        for _, descriptor in reversed(descriptors):
            os.close(descriptor)


def descriptor_mount_id(descriptor: int) -> str:
    """Obtain the held object's mount ID, rather than infer it from st_dev."""
    with Path(f"/proc/self/fdinfo/{descriptor}").open(encoding="ascii") as handle:
        info = handle.read(4097)
    values = [line.split(":", 1)[1].strip() for line in info.splitlines()
              if line.startswith("mnt_id:")]
    if len(info) > 4096 or len(values) != 1 or not values[0].isdigit():
        raise ValueError("retention descriptor mount identity is unprovable")
    return values[0]


def descriptor_filesystem_type(descriptor: int) -> int:
    """Read fstatfs type from the same held object using the native libc ABI."""
    library = ctypes.CDLL(None, use_errno=True)
    library.fstatfs.argtypes = (ctypes.c_int, ctypes.c_void_p)
    library.fstatfs.restype = ctypes.c_int
    # statfs starts with native long f_type; reserve ample aligned trailing space
    # without depending on architecture-specific layouts of the unused fields.
    buffer = (ctypes.c_long * 32)()
    if library.fstatfs(descriptor, ctypes.byref(buffer)) != 0:
        raise OSError(ctypes.get_errno(), "retention descriptor filesystem proof failed")
    return buffer[0] & 0xFFFFFFFF
