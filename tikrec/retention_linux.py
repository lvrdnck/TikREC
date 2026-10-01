"""Pinned Linux removal usable only inside enforced managed-service exclusion."""

import ctypes
import hashlib
import os
from pathlib import Path

from .managed_paths import absolute_path, check_permissions
from .managed_registry import current


class HeldArtifact:
    """Retain no-follow artifact/parent identities under exclusive service authority."""

    def __init__(self, path: Path, expected) -> None:
        self.path, self.expected = absolute_path(path), expected
        self.descriptor = self.parent = None
        self.enter_cleanup_error = None
        self._proved = None

    def __enter__(self):
        try:
            self._authority()
            if self.path != current().root / self.expected.relative_path:
                raise ValueError("managed artifact is outside its authorized root")
            self.parent = os.open(self.path.parent, os.O_RDONLY | os.O_DIRECTORY
                                  | os.O_NOFOLLOW | os.O_CLOEXEC)
            flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC
            if self.expected.kind == "directory":
                flags |= os.O_DIRECTORY
            self.descriptor = os.open(self.path.name, flags, dir_fd=self.parent)
            self._prove_identity()
            return self
        except BaseException:
            try:
                self.close()
            except BaseException as error:
                self.enter_cleanup_error = error
            raise

    def __exit__(self, *_exc) -> None:
        self.close()

    def close(self) -> None:
        """Close both pinned resources, including partial acquisition."""
        try:
            if self.descriptor is not None:
                descriptor, self.descriptor = self.descriptor, None
                os.close(descriptor)
        finally:
            if self.parent is not None:
                parent, self.parent = self.parent, None
                os.close(parent)

    def rename(self, destination: Path) -> None:
        """Quarantine without overwriting any occupied name, using the pinned parent."""
        if destination.parent != self.path.parent:
            raise ValueError("managed quarantine must remain in its pinned parent")
        self._authority()
        self._prove_identity()
        libc = ctypes.CDLL(None, use_errno=True)
        try:
            rename = libc.renameat2
        except AttributeError:
            raise ValueError("Linux no-replace quarantine is unavailable") from None
        rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int,
                           ctypes.c_char_p, ctypes.c_uint]
        rename.restype = ctypes.c_int
        # RENAME_NOREPLACE supplies destination exclusion; UID ownership and the
        # service gate supply source exclusion for the entire proof/removal step.
        if rename(self.parent, os.fsencode(self.path.name), self.parent,
                  os.fsencode(destination.name), 1):
            raise OSError(ctypes.get_errno(), "managed no-replace quarantine failed")
        self.path = destination
        self._prove_identity()

    def prove(self, digest: str | None) -> None:
        """Bind final bytes or empty directory membership to the held object."""
        self._authority()
        self._prove_identity()
        if self.expected.kind == "directory":
            if digest is not None or os.listdir(self.descriptor):
                raise ValueError("managed retained directory has late children")
            self._proved = True
            return
        if digest is None:
            raise ValueError("managed removal lacks authorized byte proof")
        before = os.fstat(self.descriptor)
        actual, size, offset = hashlib.sha256(), 0, 0
        while chunk := os.pread(self.descriptor, 64 * 1024, offset):
            actual.update(chunk)
            size += len(chunk)
            offset += len(chunk)
        after = os.fstat(self.descriptor)
        if (actual.hexdigest() != digest or size != self.expected.size
                or (before.st_size, before.st_mtime_ns, before.st_ctime_ns)
                != (after.st_size, after.st_mtime_ns, after.st_ctime_ns)):
            raise ValueError("managed held artifact bytes changed")
        self._prove_identity()
        self._proved = (after.st_size, after.st_mtime_ns, after.st_ctime_ns)

    def delete(self) -> None:
        """Remove the proven name while enforced namespace/data exclusion remains held."""
        self._authority()
        self._prove_identity()
        details = os.fstat(self.descriptor)
        if self._proved is None or (self.expected.kind == "file" and self._proved
                                    != (details.st_size, details.st_mtime_ns, details.st_ctime_ns)):
            raise ValueError("managed artifact changed after byte proof")
        if self.expected.kind == "directory":
            if os.listdir(self.descriptor):
                raise ValueError("managed retained directory has late children")
            os.rmdir(self.path.name, dir_fd=self.parent)
        else:
            os.unlink(self.path.name, dir_fd=self.parent)

    def sync_parent(self) -> None:
        """Publish mutation on the held parent before the executor journals deletion."""
        self._authority()
        os.fsync(self.parent)

    def _authority(self):
        authority = current()
        if authority is None:
            raise ValueError("Linux removal requires managed service authority")
        if authority.root not in self.path.parents:
            raise ValueError("Linux removal is outside managed storage")
        authority.assert_exclusive()
        if self.parent is not None:
            held, named = os.fstat(self.parent), self.path.parent.lstat()
            if (held.st_dev, held.st_ino) != (named.st_dev, named.st_ino):
                raise ValueError("managed pinned parent changed")

    def _prove_identity(self):
        held = os.fstat(self.descriptor)
        named = os.stat(self.path.name, dir_fd=self.parent, follow_symlinks=False)
        item = self.expected
        directory = item.kind == "directory"
        check_permissions(self.descriptor, held, current().uid, directory=directory)
        keys = ("st_mode", "st_dev", "st_ino", "st_nlink")
        expected = (item.mode, item.device, item.inode, item.link_count)
        if not directory:
            keys += ("st_size", "st_mtime_ns")
            expected += (item.size, item.mtime_ns)
        if (tuple(getattr(held, key) for key in keys) != expected
                or tuple(getattr(named, key) for key in keys) != expected):
            raise ValueError("managed held artifact identity changed")
