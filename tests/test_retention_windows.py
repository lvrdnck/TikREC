"""Native handle operations must preserve object identity at actual mutation."""

import hashlib
import os

import pytest

from tikrec.retention_authorization import fingerprint
from tikrec.retention_locality import local_volume
from tikrec.retention_windows import HeldArtifact


pytestmark = pytest.mark.skipif(os.name != "nt", reason="native Windows handle deletion")


@pytest.mark.parametrize("directory", [False, True])
def test_exclusive_object_cannot_be_substituted_after_proof(tmp_path, directory):
    original, private = tmp_path / "original", tmp_path / "private"
    original.mkdir() if directory else original.write_bytes(b"authorized")
    item = fingerprint(tmp_path, original, directory=directory, volume=local_volume(tmp_path))
    digest = None if directory else hashlib.sha256(b"authorized").hexdigest()
    with HeldArtifact(original, item) as held:
        held.rename(private)
        held.prove(digest)
        with pytest.raises(PermissionError):
            private.rename(tmp_path / "saved")
        held.delete()
    assert not original.exists() and not private.exists()


@pytest.mark.parametrize("directory", [False, True])
def test_atomic_rename_refuses_occupied_destination(tmp_path, directory):
    original, private = tmp_path / "original", tmp_path / "private"
    original.mkdir() if directory else original.write_bytes(b"authorized")
    private.mkdir() if directory else private.write_bytes(b"unexpected")
    item = fingerprint(tmp_path, original, directory=directory, volume=local_volume(tmp_path))
    with HeldArtifact(original, item) as held:
        with pytest.raises(OSError):
            held.rename(private)
    assert original.exists() and private.exists()
    if not directory:
        assert private.read_bytes() == b"unexpected"


def test_wrong_held_bytes_preserve_authorized_file(tmp_path):
    original = tmp_path / "original"
    original.write_bytes(b"authorized")
    item = fingerprint(tmp_path, original, directory=False, volume=local_volume(tmp_path))
    with HeldArtifact(original, item) as held:
        with pytest.raises(ValueError, match="byte proof"):
            held.prove("0" * 64)
    assert original.read_bytes() == b"authorized"


def test_directory_disposition_refuses_late_child(tmp_path):
    original = tmp_path / "original"
    original.mkdir()
    item = fingerprint(tmp_path, original, directory=True, volume=local_volume(tmp_path))
    with HeldArtifact(original, item) as held:
        held.prove(None)
        (original / "late").write_bytes(b"keep")
        with pytest.raises(OSError):
            held.delete()
    assert (original / "late").read_bytes() == b"keep"


@pytest.mark.parametrize("directory", [False, True])
def test_held_object_prevents_parent_substitution(tmp_path, directory):
    parent = tmp_path / "parent"
    parent.mkdir()
    original = parent / "original"
    original.mkdir() if directory else original.write_bytes(b"authorized")
    item = fingerprint(tmp_path, original, directory=directory, volume=local_volume(tmp_path))
    with HeldArtifact(original, item):
        with pytest.raises(PermissionError):
            parent.rename(tmp_path / "different-parent")
    assert original.exists()


def test_case_insensitive_destination_collision_is_not_overwritten(tmp_path):
    original, occupied = tmp_path / "source", tmp_path / "PRIVATE"
    original.write_bytes(b"authorized")
    occupied.write_bytes(b"keep")
    item = fingerprint(tmp_path, original, directory=False, volume=local_volume(tmp_path))
    with HeldArtifact(original, item) as held:
        with pytest.raises(OSError):
            held.rename(tmp_path / "private")
    assert occupied.read_bytes() == b"keep" and original.read_bytes() == b"authorized"
