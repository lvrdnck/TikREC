"""Root lifecycle leases exclude destructive retention across processes."""

import os
from pathlib import Path
import subprocess
import sys
import time

import pytest

import tikrec.lifecycle_lock as lifecycle_module
from tikrec.lifecycle_lock import (LOCK_NAME, LifecycleBusy, acquire_lifecycle,
                                   acquire_writer_roots)


_HOLDER = """
import sys
from pathlib import Path
from tikrec.lifecycle_lock import acquire_lifecycle
with acquire_lifecycle(Path(sys.argv[1]), sys.argv[2]):
    print('held', flush=True)
    sys.stdin.readline()
"""


def holder(root, mode):
    """Start one real child process and wait until its OS lease is held."""
    process = subprocess.Popen(
        [sys.executable, "-c", _HOLDER, str(root), mode],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True,
    )
    assert process.stdout.readline().strip() == "held"
    return process


def released_lease(root, mode):
    """Allow Windows a brief handle teardown window after forced termination."""
    deadline = time.monotonic() + 3
    while True:
        try:
            return acquire_lifecycle(root, mode)
        except LifecycleBusy:
            if time.monotonic() >= deadline:
                raise
            time.sleep(0.02)


def test_same_process_writers_coexist_and_retention_is_exclusive(tmp_path):
    with acquire_lifecycle(tmp_path, "writer") as first:
        with acquire_lifecycle(tmp_path, "writer") as second:
            first.assert_held()
            second.assert_held()
            if os.name == "nt":
                assert first.slot != second.slot
            with pytest.raises(LifecycleBusy):
                acquire_lifecycle(tmp_path, "retention")
    with acquire_lifecycle(tmp_path, "retention") as exclusive:
        exclusive.assert_held()
        with pytest.raises(LifecycleBusy):
            acquire_lifecycle(tmp_path, "writer")
    assert (tmp_path / LOCK_NAME).is_file()


@pytest.mark.parametrize("mode,other", [
    ("writer", "retention"), ("retention", "writer"),
])
def test_cross_process_incompatible_leases_fail_nonblocking(tmp_path, mode, other):
    process = holder(tmp_path, mode)
    try:
        with pytest.raises(LifecycleBusy):
            acquire_lifecycle(tmp_path, other)
        if mode == "writer":
            with acquire_lifecycle(tmp_path, "writer") as second:
                second.assert_held()
        process.stdin.write("\n")
        process.stdin.flush()
        assert process.wait(timeout=10) == 0
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=10)
        process.stdin.close()
        process.stdout.close()
        process.stderr.close()
    with acquire_lifecycle(tmp_path, other) as released:
        released.assert_held()


def test_process_termination_releases_os_lock(tmp_path):
    process = holder(tmp_path, "writer")
    try:
        with pytest.raises(LifecycleBusy):
            acquire_lifecycle(tmp_path, "retention")
        process.kill()
        assert process.wait(timeout=10) != 0
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=10)
        process.stdin.close()
        process.stdout.close()
        process.stderr.close()
    with released_lease(tmp_path, "retention") as released:
        released.assert_held()


def test_lock_file_redirect_and_hard_link_fail_closed(tmp_path, monkeypatch):
    with acquire_lifecycle(tmp_path, "writer"):
        pass
    lock = tmp_path / LOCK_NAME
    original = Path.lstat

    def redirected(path):
        details = original(path)
        if path != lock:
            return details
        from types import SimpleNamespace
        values = {name: getattr(details, name) for name in
                  ("st_mode", "st_size", "st_dev", "st_ino", "st_nlink")}
        values["st_file_attributes"] = 0x400
        return SimpleNamespace(**values)

    monkeypatch.setattr(Path, "lstat", redirected)
    with pytest.raises(ValueError, match="lock file"):
        acquire_lifecycle(tmp_path, "writer")


def test_multiply_linked_lock_file_is_refused(tmp_path):
    with acquire_lifecycle(tmp_path, "writer"):
        pass
    (tmp_path / "second-link").hardlink_to(tmp_path / LOCK_NAME)
    with pytest.raises(ValueError, match="lock file"):
        acquire_lifecycle(tmp_path, "retention")


def test_manual_finalization_can_cover_parts_and_output_roots(tmp_path):
    parts_root, output_root = tmp_path / "parts", tmp_path / "output"
    parts_root.mkdir()
    output_root.mkdir()
    with acquire_writer_roots(parts_root, output_root):
        for root in (parts_root, output_root):
            with pytest.raises(LifecycleBusy):
                acquire_lifecycle(root, "retention")


class _CloseFault:
    """Forward a real lease handle and fault after closing it once."""

    def __init__(self, handle, failure=SystemExit):
        self.handle, self.failure, self.closes = handle, failure, 0

    def __getattr__(self, name):
        return getattr(self.handle, name)

    def close(self):
        self.closes += 1
        self.handle.close()
        raise self.failure("second handle close fault")


@pytest.mark.parametrize("mode", ["writer", "retention"])
@pytest.mark.parametrize("unlock_fault", [False, True])
def test_teardown_faults_release_registry_and_writer_slot_once(
        tmp_path, monkeypatch, mode, unlock_fault):
    lease = acquire_lifecycle(tmp_path, mode)
    key = lease.key
    wrapper = _CloseFault(lease.handle)
    lease.handle = wrapper
    real_unlock = lifecycle_module._unlock
    unlocks = []

    def unlock_then_fault(*args):
        unlocks.append(True)
        real_unlock(*args)
        if unlock_fault:
            raise KeyboardInterrupt("first unlock fault")

    with monkeypatch.context() as scoped:
        scoped.setattr(lifecycle_module, "_unlock", unlock_then_fault)
        with pytest.raises(KeyboardInterrupt if unlock_fault else SystemExit,
                           match="first unlock fault" if unlock_fault else
                           "second handle close fault"):
            lease.close()
    assert len(unlocks) == wrapper.closes == 1
    assert key not in lifecycle_module._registry
    assert key not in lifecycle_module._occupied
    lease.close()  # A repeated call cannot release another owner's slot.
    assert len(unlocks) == wrapper.closes == 1
    with acquire_lifecycle(tmp_path, mode) as next_lease:
        next_lease.assert_held()


def test_acquisition_fault_precedes_handle_cleanup_and_leaves_no_owner(
        tmp_path, monkeypatch):
    real_fdopen = lifecycle_module.os.fdopen
    real_identity = lifecycle_module._identity
    cleanup = []
    wrappers = []

    def wrapping_fdopen(*args, **kwargs):
        wrapper = _CloseFault(real_fdopen(*args, **kwargs))
        wrappers.append(wrapper)
        return wrapper

    def fail_acquired_handle(artifact):
        if isinstance(artifact, _CloseFault):
            raise ValueError("first acquisition identity fault")
        return real_identity(artifact)

    with monkeypatch.context() as scoped:
        scoped.setattr(lifecycle_module.os, "fdopen", wrapping_fdopen)
        scoped.setattr(lifecycle_module, "_identity", fail_acquired_handle)
        with pytest.raises(ValueError, match="first acquisition identity fault"):
            acquire_lifecycle(tmp_path, "writer", cleanup_errors=cleanup)
    key = os.path.normcase(str(tmp_path))
    assert len(wrappers) == wrappers[0].closes == 1
    assert len(cleanup) == 1 and isinstance(cleanup[0], SystemExit)
    assert key not in lifecycle_module._registry
    assert key not in lifecycle_module._occupied
    with acquire_lifecycle(tmp_path, "writer") as lease:
        lease.assert_held()


def test_new_lock_setup_fault_precedes_descriptor_close_fault(tmp_path, monkeypatch):
    real_close = lifecycle_module.os.close
    cleanup = []

    def fail_truncate(*_args):
        raise ValueError("first lifecycle lock setup fault")

    def close_then_fault(descriptor):
        real_close(descriptor)
        raise SystemExit("second lifecycle descriptor close fault")

    with monkeypatch.context() as scoped:
        scoped.setattr(lifecycle_module.os, "ftruncate", fail_truncate)
        scoped.setattr(lifecycle_module.os, "close", close_then_fault)
        with pytest.raises(ValueError, match="first lifecycle lock setup fault"):
            lifecycle_module._open_lock(tmp_path, cleanup)
    assert len(cleanup) == 1 and isinstance(cleanup[0], SystemExit)
    assert not lifecycle_module._registry and not lifecycle_module._occupied
    with acquire_lifecycle(tmp_path, "retention") as lease:
        lease.assert_held()


@pytest.mark.skipif(os.name != "nt", reason="Windows writer slots only")
def test_registration_fault_rolls_back_slot_and_keeps_first_cause(
        tmp_path, monkeypatch):
    key = os.path.normcase(str(tmp_path))
    real_fdopen = lifecycle_module.os.fdopen
    cleanup = []

    class FaultSet(set):
        def add(self, value):
            super().add(value)
            raise ValueError("first writer slot registration fault")

    def wrapping_fdopen(*args, **kwargs):
        return _CloseFault(real_fdopen(*args, **kwargs))

    with monkeypatch.context() as scoped:
        lifecycle_module._occupied[key] = FaultSet()
        scoped.setattr(lifecycle_module.os, "fdopen", wrapping_fdopen)
        with pytest.raises(ValueError, match="first writer slot registration fault"):
            acquire_lifecycle(tmp_path, "writer", cleanup_errors=cleanup)
    assert len(cleanup) == 1 and isinstance(cleanup[0], SystemExit)
    assert key not in lifecycle_module._registry
    assert key not in lifecycle_module._occupied
    with acquire_lifecycle(tmp_path, "writer") as lease:
        lease.assert_held()
