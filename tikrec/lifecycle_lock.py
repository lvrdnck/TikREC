"""Cross-process root leases separating writers from destructive retention."""

from __future__ import annotations

import os
import stat
import threading
from contextlib import ExitStack, contextmanager
from pathlib import Path

from .retention_locality import local_volume, proven_local
from .retention_paths import local_path


LOCK_NAME = ".tikrec-lifecycle.lock"
_WRITER_SLOTS = 64
_registry_guard = threading.RLock()
_registry: dict[str, dict[str, int]] = {}
_occupied: dict[str, set[int]] = {}


class LifecycleBusy(ValueError):
    """Another lifecycle operation owns the root's incompatible lease."""


class LifecycleLease:
    """One open OS-backed writer or exclusive retention lease."""

    def __init__(self, root: Path, mode: str, handle, slot: int | None,
                 identity: tuple, key: str) -> None:
        self.root, self.mode, self.handle = root, mode, handle
        self.slot, self.identity, self.key = slot, identity, key
        self.closed = False

    def __enter__(self) -> LifecycleLease:
        return self

    def __exit__(self, *_exc) -> None:
        self.close()

    def assert_held(self) -> None:
        """Reject a lost descriptor or replaced persistent lock file."""
        if (self.closed or self.handle.closed
                or _identity(self.root / LOCK_NAME) != self.identity
                or _identity(self.handle) != self.identity):
            raise ValueError("lifecycle lease identity changed")

    def close(self) -> None:
        """Release this process's OS lock and registry ownership once."""
        with _registry_guard:
            if self.closed:
                return
            self.closed = True
            try:
                if not self.handle.closed:
                    _unlock(self.handle, self.mode, self.slot)
            finally:
                self.handle.close()
                active = _registry[self.key]
                active[self.mode] -= 1
                if self.slot is not None and self.mode == "writer":
                    _occupied[self.key].remove(self.slot)
                if not any(active.values()):
                    del _registry[self.key]
                    _occupied.pop(self.key, None)


def acquire_lifecycle(root: Path, mode: str) -> LifecycleLease:
    """Acquire a nonblocking shared writer or exclusive retention root lease."""
    if mode not in {"writer", "retention"}:
        raise ValueError("unsupported lifecycle lease mode")
    scope = local_path(Path(root), directory=True)
    if not proven_local(scope) or local_volume(scope) is None:
        raise ValueError("lifecycle root locality could not be proven")
    key = os.path.normcase(str(scope))
    with _registry_guard:
        active = _registry.get(key, {"writer": 0, "retention": 0})
        if active["retention"] or (mode == "retention" and active["writer"]):
            raise LifecycleBusy("recording root has a conflicting lifecycle lease")
        handle = _open_lock(scope)
        try:
            slot = _lock(handle, mode, _occupied.get(key, set()))
            identity = _identity(handle)
            if (identity is None or _identity(scope / LOCK_NAME) != identity
                    or local_volume(scope / LOCK_NAME) != local_volume(scope)):
                raise ValueError("lifecycle lock file changed during acquisition")
        except BaseException:
            handle.close()
            raise
        active[mode] += 1
        _registry[key] = active
        if slot is not None and mode == "writer":
            _occupied.setdefault(key, set()).add(slot)
        return LifecycleLease(scope, mode, handle, slot, identity, key)


@contextmanager
def acquire_writer_roots(*roots: Path):
    """Hold compatible writer leases for every root an operation may modify."""
    with ExitStack() as stack:
        # A stable order avoids cross-root waits if blocking leases are added later.
        for root in sorted({Path(os.path.abspath(path)) for path in roots}, key=str):
            stack.enter_context(acquire_lifecycle(root, "writer"))
        yield


def _open_lock(root: Path):
    path = root / LOCK_NAME
    flags = os.O_RDWR | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    created = False
    try:
        descriptor = os.open(path, flags | os.O_CREAT | os.O_EXCL, 0o600)
        created = True
    except FileExistsError:
        descriptor = os.open(path, flags)
    try:
        if (_identity(descriptor) is None
                or _identity(path) != _identity(descriptor)):
            raise ValueError("lifecycle lock file is redirected or ambiguous")
        if os.fstat(descriptor).st_size < _WRITER_SLOTS:
            # A crashed creator may leave a short file; extending never releases locks.
            os.ftruncate(descriptor, _WRITER_SLOTS)
            os.fsync(descriptor)
        if created and os.name != "nt":
            parent = os.open(root, os.O_RDONLY)
            try:
                os.fsync(parent)
            finally:
                os.close(parent)
        return os.fdopen(descriptor, "r+b", buffering=0)
    except BaseException:
        os.close(descriptor)
        raise


def _identity(artifact) -> tuple | None:
    if isinstance(artifact, int):
        details = os.fstat(artifact)
    elif hasattr(artifact, "fileno"):
        details = os.fstat(artifact.fileno())
    else:
        try:
            details = artifact.lstat()
        except FileNotFoundError:
            return None
    if (not stat.S_ISREG(details.st_mode) or details.st_nlink != 1
            or getattr(details, "st_file_attributes", 0) & 0x400):
        return None
    return (details.st_mode, details.st_size, details.st_dev, details.st_ino,
            getattr(details, "st_file_attributes", 0))


def _lock(handle, mode: str, occupied: set[int]) -> int | None:
    if os.name != "nt":
        import fcntl
        try:
            fcntl.flock(handle.fileno(),
                        (fcntl.LOCK_SH if mode == "writer" else fcntl.LOCK_EX)
                        | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise LifecycleBusy("recording root has a conflicting lifecycle lease") from error
        return None
    import msvcrt
    slots = range(_WRITER_SLOTS) if mode == "writer" else (0,)
    for slot in slots:
        if mode == "writer" and slot in occupied:
            continue
        handle.seek(slot)
        try:
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK,
                           1 if mode == "writer" else _WRITER_SLOTS)
            return slot
        except OSError:
            continue
    raise LifecycleBusy("recording root has a conflicting lifecycle lease")


def _unlock(handle, mode: str, slot: int | None) -> None:
    if os.name != "nt":
        import fcntl
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        return
    import msvcrt
    handle.seek(0 if slot is None else slot)
    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK,
                   1 if mode == "writer" else _WRITER_SLOTS)
