"""Pinned Linux ownership proof for a service-controlled namespace."""

from __future__ import annotations

import errno
import os
import stat
from pathlib import Path


class ProtectedPath:
    """Hold every no-follow component and reject identity or permission changes."""

    def __init__(self, path: Path, uid: int, *, directory: bool = True) -> None:
        self.path = absolute_path(path)
        self.components: list[tuple[Path, int, tuple]] = []
        try:
            current = Path("/")
            descriptor = os.open(current, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            self._remember(current, descriptor, 0, True)
            for index, name in enumerate(self.path.parts[1:]):
                current = current / name
                final = index == len(self.path.parts) - 2
                is_directory = not final or directory
                flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC
                if is_directory:
                    flags |= os.O_DIRECTORY
                descriptor = os.open(name, flags, dir_fd=self.components[-1][1])
                # All mutation-controlling ancestors belong to the administrator.
                self._remember(current, descriptor, uid if final else 0, is_directory)
            self.assert_held()
        except BaseException:
            self.close()
            raise

    @property
    def descriptor(self) -> int:
        """Return the held endpoint for descriptor-relative operations."""
        return self.components[-1][1]

    def _remember(self, path, descriptor, uid, directory):
        try:
            details = os.fstat(descriptor)
            check_permissions(descriptor, details, uid, directory=directory)
            self.components.append((path, descriptor, identity(details)))
        except BaseException:
            os.close(descriptor)
            raise

    def assert_held(self) -> None:
        """Recheck pinned ancestors and their names, including access/default ACLs."""
        for path, descriptor, expected in self.components:
            held, named = os.fstat(descriptor), path.lstat()
            if identity(held) != expected or identity(named) != expected:
                raise ValueError("managed namespace identity changed")
            check_permissions(descriptor, held, expected[2],
                              directory=stat.S_ISDIR(held.st_mode))

    def close(self) -> None:
        """Release each pinned component once, including partial acquisition."""
        while self.components:
            os.close(self.components.pop()[1])


def absolute_path(path: Path) -> Path:
    """Reject normalization, relative components, or an alternate root spelling."""
    value = os.fspath(path)
    if not value.startswith("/") or "\x00" in value or value != os.path.normpath(value):
        raise ValueError("managed path must be a canonical absolute Linux path")
    return Path(value)


def identity(details) -> tuple:
    """Bind ownership and permissions alongside the physical object identity."""
    return details.st_dev, details.st_ino, details.st_uid, details.st_gid, details.st_mode


def check_permissions(descriptor: int, details, uid: int, *, directory: bool) -> None:
    """Allow only one trusted UID to write, with no ACL or hard-link escape."""
    kind = stat.S_ISDIR if directory else stat.S_ISREG
    if (not kind(details.st_mode) or details.st_uid != uid
            or details.st_mode & 0o7022 or not directory and details.st_nlink != 1):
        raise ValueError("managed storage ownership or write exclusion is unsafe")
    for name in ("system.posix_acl_access", "system.posix_acl_default"):
        try:
            os.getxattr(descriptor, name)
        except OSError as error:
            if error.errno not in {errno.ENODATA, errno.ENOTSUP}:
                raise ValueError("managed ACL exclusion could not be proven") from error
        else:
            # Conservative refusal also covers inherited ACL grants and masks.
            raise ValueError("managed storage ACLs are unsupported")


def check_tree(path: Path, uid: int, *, trusted_files: tuple[Path, ...] = ()) -> None:
    """Check service-created descendants without following links or mount escapes."""
    from .retention_locality import local_volume

    volume = local_volume(path)
    if volume is None:
        raise ValueError("managed storage locality could not be proven")
    pending = [path]
    while pending:
        current = pending.pop()
        details = current.lstat()
        directory = stat.S_ISDIR(details.st_mode)
        flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC
        if directory:
            flags |= os.O_DIRECTORY
        if not directory and not stat.S_ISREG(details.st_mode):
            raise ValueError("managed storage contains a redirected or special artifact")
        descriptor = os.open(current, flags)
        try:
            if identity(details) != identity(os.fstat(descriptor)):
                raise ValueError("managed artifact identity changed")
            check_permissions(descriptor, details, 0 if current in trusted_files else uid,
                              directory=directory)
            if local_volume(current) != volume:
                raise ValueError("managed artifact crosses a storage volume")
            if directory:
                pending.extend(current / name for name in os.listdir(descriptor))
        finally:
            os.close(descriptor)
