"""Short cross-process authority shared by config promotion and retention removal."""

from __future__ import annotations

import errno
import os
import stat
import threading
import time
from contextlib import contextmanager
from pathlib import Path


_condition = threading.Condition()
_owners: dict[str, tuple[int, str, object]] = {}


class PolicyLease:
    """One persistent lock-file identity held until an atomic boundary finishes."""

    def __init__(self, path, descriptor):
        self.path, self.descriptor = path, descriptor
        self.identity = _identity(os.fstat(descriptor))

    def assert_held(self) -> None:
        """Refuse a replaced or redirected lock before committing authority."""
        if (_identity(self.path.lstat()) != self.identity
                or _identity(os.fstat(self.descriptor)) != self.identity):
            raise ValueError("retention policy lock identity changed")


@contextmanager
def policy_lock(configuration_path: Path, mode: str = "retention", *,
                cleanup_errors: list[BaseException] | None = None):
    """Serialize config promotion and removal, collecting secondary close faults."""
    if mode not in {"write", "retention"}:
        raise ValueError("invalid retention policy lock mode")
    source = Path(os.path.abspath(configuration_path))
    try:
        details = source.lstat()
    except FileNotFoundError:
        details = None
    redirected = details is not None and (stat.S_ISLNK(details.st_mode)
                                          or getattr(details, "st_file_attributes", 0) & 0x400)
    if mode == "retention" and redirected:
        raise ValueError("retention policy configuration redirects")
    if not redirected:
        source = source.resolve()  # Includes Windows 8.3 aliases of an existing file.
    # Resolve parent aliases, but do not follow a config-file symlink: promotion
    # replaces that directory entry, as ConfigurationStore has always done.
    parent = source.parent.resolve()
    path = parent / f".{source.name}.retention-policy.lock"
    key, owner = os.path.normcase(str(path)), threading.get_ident()
    nested = None
    with _condition:
        while key in _owners:
            thread, previous_mode, lease = _owners[key]
            if thread == owner:
                if mode != "write" or previous_mode != "write":
                    raise ValueError("policy update cannot run inside retention mutation")
                nested = lease
                break
            _condition.wait()
        if nested is None:
            _owners[key] = (owner, mode, None)
    if nested is not None:
        nested.assert_held()
        yield nested
        return
    descriptor = None
    primary_error: BaseException | None = None
    try:
        parent.mkdir(parents=True, exist_ok=True)
        flags = os.O_RDWR | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        try:
            descriptor = os.open(path, flags | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            descriptor = os.open(path, flags)
        details = os.fstat(descriptor)
        if _identity(details, allow_empty=True) != _identity(path.lstat(), allow_empty=True):
            raise ValueError("retention policy lock identity changed")
        if details.st_size == 0:
            os.ftruncate(descriptor, 1)  # Recover an empty lock left by a crash.
        lease = PolicyLease(path, descriptor)
        lease.assert_held()
        _lock(descriptor)
        lease.assert_held()
        with _condition:
            _owners[key] = (owner, mode, lease)
        yield lease
    except BaseException as error:
        # A body or acquisition fault precedes every teardown fault.
        primary_error = error
        raise
    finally:
        # Closing releases both flock and Windows byte-range ownership. Keep
        # its fault before owner/notification faults, while attempting each
        # remaining cleanup action exactly once.
        faults: list[BaseException] = []
        try:
            if descriptor is not None:
                os.close(descriptor)
        except BaseException as error:
            faults.append(error)
        try:
            with _condition:
                try:
                    _owners.pop(key, None)
                except BaseException as error:
                    faults.append(error)
                try:
                    _condition.notify_all()
                except BaseException as error:
                    faults.append(error)
        except BaseException as error:
            faults.append(error)
        if primary_error is not None:
            if cleanup_errors is not None:
                cleanup_errors.extend(faults)
        elif faults:
            if cleanup_errors is not None:
                cleanup_errors.extend(faults[1:])
            raise faults[0]


def _identity(details, *, allow_empty=False):
    if (not stat.S_ISREG(details.st_mode) or details.st_nlink != 1
            or details.st_size not in ({0, 1} if allow_empty else {1})
            or getattr(details, "st_file_attributes", 0) & 0x400):
        raise ValueError("retention policy lock is redirected or ambiguous")
    return details.st_dev, details.st_ino


def _lock(descriptor):
    if os.name != "nt":
        import fcntl
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        return
    import msvcrt
    while True:
        try:
            os.lseek(descriptor, 0, os.SEEK_SET)
            msvcrt.locking(descriptor, msvcrt.LK_NBLCK, 1)
            return
        except OSError as error:
            if error.errno not in {errno.EACCES, errno.EAGAIN, errno.EDEADLK}:
                raise
            time.sleep(0.01)  # Wait only on another short commit/removal boundary.
