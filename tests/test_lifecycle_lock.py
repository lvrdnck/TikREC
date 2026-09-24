"""Root lifecycle leases exclude destructive retention across processes."""

import os
from pathlib import Path
import subprocess
import sys
import time

import pytest

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
