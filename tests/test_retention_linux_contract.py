"""Disposable Linux counterexamples to pathname-based exact-object deletion.

These are evidence tests, not a deletion backend. Destructive production
execution must remain refused while other processes can replace proven names.
"""

import ctypes
import errno
import hashlib
import os
import subprocess
import sys

import pytest

from tests.test_retention_delete_cli import call
from tests.test_retention_execute import fixture


if sys.platform.startswith("linux"):
    import fcntl


pytestmark = pytest.mark.skipif(not sys.platform.startswith("linux"),
                              reason="Linux namespace/descriptor semantics")


def replace_in_other_process(path, saved, directory):
    """Act as a non-cooperating same-UID namespace writer on disposable paths."""
    subprocess.run([sys.executable, "-c", """
import sys
from pathlib import Path
path, saved = map(Path, sys.argv[1:3])
path.rename(saved)
if sys.argv[3] == 'directory':
    path.mkdir()
else:
    path.write_bytes(b'unapproved replacement')
""", str(path), str(saved), "directory" if directory else "file"], check=True)


@pytest.mark.parametrize("directory", [False, True])
@pytest.mark.parametrize("name", ["original", ".tikrec-retention-private"])
def test_held_proven_object_and_advisory_lock_do_not_bind_unlink(tmp_path, directory, name):
    path, saved = tmp_path / name, tmp_path / "saved-approved"
    path.mkdir() if directory else path.write_bytes(b"approved")
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    parent = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        before = os.fstat(descriptor)
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if not directory:
            assert hashlib.sha256(os.read(descriptor, 100)).digest() == hashlib.sha256(b"approved").digest()
        # Deterministically schedule replacement after the final proof. The
        # held inode and its bytes stay intact; a later unlink targets another.
        replace_in_other_process(path, saved, directory)
        assert os.fstat(descriptor).st_ino == before.st_ino
        assert saved.stat().st_ino == before.st_ino
        assert path.stat().st_ino != before.st_ino
        if directory:
            os.rmdir(path.name, dir_fd=parent)
        else:
            os.unlink(path.name, dir_fd=parent)
        assert not path.exists() and saved.exists()
        if not directory:
            assert saved.read_bytes() == b"approved"
    finally:
        os.close(parent)
        os.close(descriptor)


@pytest.mark.parametrize("directory", [False, True])
def test_atomic_no_replace_preserves_occupied_destination_but_not_source_identity(tmp_path, directory):
    source, destination, saved = tmp_path / "source", tmp_path / "private", tmp_path / "saved"
    if directory:
        source.mkdir()
        destination.mkdir()
    else:
        source.write_bytes(b"approved")
        destination.write_bytes(b"occupied")
    library = ctypes.CDLL(None, use_errno=True)
    library.renameat2.argtypes = (ctypes.c_int, ctypes.c_char_p, ctypes.c_int,
                                  ctypes.c_char_p, ctypes.c_uint)
    library.renameat2.restype = ctypes.c_int
    parent = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    held = os.open(source, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        identity = os.fstat(held).st_ino
        assert library.renameat2(parent, b"source", parent, b"private", 1) == -1
        assert ctypes.get_errno() == errno.EEXIST
        assert source.stat().st_ino == identity and destination.exists()
        os.rmdir(destination) if directory else destination.unlink()
        replace_in_other_process(source, saved, directory)
        assert library.renameat2(parent, b"source", parent, b"private", 1) == 0
        assert destination.stat().st_ino != identity and saved.stat().st_ino == identity
        assert os.fstat(held).st_ino == identity
    finally:
        os.close(held)
        os.close(parent)


def test_wrong_bytes_can_be_written_after_hash_despite_advisory_lock(tmp_path):
    path = tmp_path / "data"
    path.write_bytes(b"approved")
    held = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
        approved_hash = hashlib.sha256(os.read(held, 100)).digest()
        subprocess.run([sys.executable, "-c",
                        "import sys; from pathlib import Path; Path(sys.argv[1]).write_bytes(b'wrong bytes')",
                        str(path)], check=True)
        os.lseek(held, 0, os.SEEK_SET)
        assert hashlib.sha256(os.read(held, 100)).digest() != approved_hash
    finally:
        os.close(held)


def test_late_children_refuse_rmdir_but_empty_substitution_is_still_removable(tmp_path):
    directory = tmp_path / "approved"
    directory.mkdir()
    held = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
    try:
        identity = os.fstat(held).st_ino
        (directory / "late-evidence").write_bytes(b"preserve")
        with pytest.raises(OSError) as refused:
            directory.rmdir()
        assert refused.value.errno == errno.ENOTEMPTY
        saved = tmp_path / "saved"
        replace_in_other_process(directory, saved, True)
        directory.rmdir()
        assert saved.stat().st_ino == identity
        assert (saved / "late-evidence").read_bytes() == b"preserve"
    finally:
        os.close(held)


@pytest.mark.parametrize("change", ["parent", "root"])
def test_held_parent_operates_on_detached_tree_after_path_replacement(tmp_path, change):
    root = tmp_path / "root"
    parent = root / "parent"
    parent.mkdir(parents=True)
    (parent / "data").write_bytes(b"approved")
    held = os.open(parent, os.O_RDONLY | os.O_DIRECTORY)
    target = root if change == "root" else parent
    saved = target.with_name("saved")
    try:
        replace_in_other_process(target, saved, True)
        if change == "root":
            parent.mkdir()
        (parent / "data").write_bytes(b"new tree")
        os.unlink("data", dir_fd=held)
        assert (parent / "data").read_bytes() == b"new tree"
        detached = saved / "parent" if change == "root" else saved
        assert not (detached / "data").exists()
    finally:
        os.close(held)


@pytest.mark.parametrize("directory", [False, True])
def test_empty_path_unlink_cannot_target_held_object(tmp_path, directory):
    path = tmp_path / "approved"
    path.mkdir() if directory else path.write_bytes(b"approved")
    held = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    library = ctypes.CDLL(None, use_errno=True)
    library.unlinkat.argtypes = (ctypes.c_int, ctypes.c_char_p, ctypes.c_int)
    library.unlinkat.restype = ctypes.c_int
    try:
        # AT_EMPTY_PATH is supported by other APIs, not by unlinkat. Adding
        # AT_REMOVEDIR cannot turn a directory handle into exact-object removal.
        assert library.unlinkat(held, b"", 0x1000 | (0x200 if directory else 0)) == -1
        assert ctypes.get_errno() == errno.EINVAL and path.exists()
    finally:
        os.close(held)


def test_public_linux_refusal_preserves_disposable_media_config_and_audit(tmp_path):
    case = fixture(tmp_path)
    root, _, session_id, config, _, audit, _ = case
    before = {str(path.relative_to(root)): path.read_bytes()
              for path in root.rglob("*") if path.is_file()}
    configuration = config.path.read_bytes()
    code, out, err = call(case, confirm=session_id)
    assert code == 1 and "destructive retention is Windows-only" in err
    assert "COMPLETE" not in out and not audit.exists()
    assert not (root / ".tikrec-lifecycle.lock").exists()
    assert config.path.read_bytes() == configuration
    assert before == {str(path.relative_to(root)): path.read_bytes()
                      for path in root.rglob("*") if path.is_file()}
    assert (root / "alpha.mp4").exists()
