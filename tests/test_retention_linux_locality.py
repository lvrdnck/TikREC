"""Native no-follow evidence and conservative Btrfs subvolume topology."""

import os
import sys
from io import StringIO
from pathlib import Path, PurePosixPath

import pytest

from tikrec import retention_linux_locality as native
from tikrec.retention_locality import _LinuxMount, _linux_volume, local_volume


pytestmark = pytest.mark.skipif(not sys.platform.startswith("linux"),
                              reason="Linux descriptor mount evidence")


def topology(kind="btrfs"):
    """Model Fedora's distinct root/home subvolume mounts on one superblock."""
    return [_LinuxMount("43", "1", (0, 35), PurePosixPath("/"), kind),
            _LinuxMount("59", "43", (0, 35), PurePosixPath("/home"), kind)]


def evidence(mount="59", device=(0, 52), magic=native.BTRFS_SUPER_MAGIC):
    """Keep each independent kernel observation explicit in topology cases."""
    return native.LinuxPathEvidence(mount, device, magic)


def test_btrfs_subvolume_device_requires_held_kernel_mount_and_type():
    path = PurePosixPath("/home/owner/recordings")
    assert _linux_volume(path, topology(), (0, 52)) is None
    result = _linux_volume(path, topology(), None, evidence=evidence())
    assert result.point == "/home" and result.identity == "59:0:52"
    # A nested subvolume must not compare equal to the authorized root volume.
    other = _linux_volume(path, topology(), None, evidence=evidence(device=(0, 60)))
    assert other != result


@pytest.mark.parametrize("observed", [
    evidence(mount="43"), evidence(mount="999"), evidence(magic=0xEF53),
])
def test_btrfs_label_cannot_override_wrong_kernel_evidence(observed):
    assert _linux_volume(PurePosixPath("/home/recordings"), topology(), None,
                         evidence=observed) is None


def test_explicit_device_mismatch_cannot_be_overridden():
    assert _linux_volume(PurePosixPath("/home/recordings"), topology(), (0, 99),
                         evidence=evidence()) is None


@pytest.mark.parametrize("kind", ["ext4", "xfs", "nfs4", "cifs", "overlay", "fuse.btrfs"])
def test_btrfs_evidence_does_not_relax_other_filesystem_mismatches(kind):
    assert _linux_volume(PurePosixPath("/home/recordings"), topology(kind), None,
                         evidence=evidence()) is None


@pytest.mark.parametrize("case", ["stack", "hidden", "orphan", "duplicate", "cycle"])
def test_kernel_mount_id_does_not_override_ambiguous_topology(case):
    mounts = topology()
    if case == "stack":
        mounts.append(_LinuxMount("60", "59", (0, 52), PurePosixPath("/home"), "btrfs"))
    elif case == "hidden":
        mounts.append(_LinuxMount("60", "43", (0, 90), PurePosixPath("/home/owner"), "nfs"))
        mounts.append(_LinuxMount("61", "59", (0, 35),
                                  PurePosixPath("/home/owner/recordings"), "btrfs"))
    elif case == "orphan":
        mounts[1] = _LinuxMount("59", "999", (0, 35), PurePosixPath("/home"), "btrfs")
    elif case == "duplicate":
        mounts.append(mounts[1])
    else:
        mounts[0] = _LinuxMount("43", "59", (0, 35), PurePosixPath("/"), "btrfs")
    assert _linux_volume(PurePosixPath("/home/owner/recordings"), mounts, None,
                         evidence=evidence()) is None


def test_native_descriptor_evidence_matches_kernel_and_is_read_only(tmp_path):
    artifact = tmp_path / "data"
    artifact.write_bytes(b"evidence")
    before = artifact.stat()
    for path in (tmp_path, artifact):
        observed = native.linux_path_evidence(path, native.read_mountinfo())
        assert observed is not None
        details = path.stat()
        assert observed.device == (os.major(details.st_dev), os.minor(details.st_dev))
        volume = local_volume(path)
        assert volume is not None and volume.identity.startswith(observed.mount_id + ":")
    assert artifact.stat() == before and artifact.read_bytes() == b"evidence"


@pytest.mark.parametrize("intermediate", [False, True])
def test_native_no_follow_rejects_links_at_every_level(tmp_path, intermediate):
    target = tmp_path / "target"
    target.mkdir()
    (target / "data").write_bytes(b"protected")
    link = tmp_path / "link"
    link.symlink_to(target if intermediate else target / "data")
    path = link / "data" if intermediate else link
    assert native.linux_path_evidence(path, native.read_mountinfo()) is None
    assert local_volume(path) is None
    assert (target / "data").read_bytes() == b"protected"


def test_missing_fifo_and_relative_paths_are_not_proven(tmp_path):
    fifo = tmp_path / "fifo"
    os.mkfifo(fifo)
    for path in (tmp_path / "missing", fifo, Path("relative")):
        assert native.linux_path_evidence(path, native.read_mountinfo()) is None


@pytest.mark.parametrize("change", ["parent", "root", "final"])
def test_replacement_after_open_is_observed_and_refused(tmp_path, monkeypatch, change):
    root = tmp_path / "root"
    parent = root / "parent"
    parent.mkdir(parents=True)
    artifact = parent / "data"
    artifact.write_bytes(b"approved")
    target = {"parent": parent, "root": root, "final": artifact}[change]
    original = native.descriptor_filesystem_type

    def swap(descriptor):
        result = original(descriptor)
        target.rename(target.with_name(target.name + "-saved"))
        if change == "final":
            target.write_bytes(b"replacement")
        else:
            target.mkdir()
            if change == "root":
                (target / "parent").mkdir()
            artifact.write_bytes(b"replacement")
        return result

    monkeypatch.setattr(native, "descriptor_filesystem_type", swap)
    assert native.linux_path_evidence(artifact, native.read_mountinfo()) is None
    assert artifact.read_bytes() == b"replacement"


def test_mount_table_change_during_observation_refuses(tmp_path, monkeypatch):
    initial = native.read_mountinfo()
    observations = iter((initial, initial + "\n"))
    monkeypatch.setattr(native, "read_mountinfo", lambda: next(observations))
    assert native.linux_path_evidence(tmp_path, initial) is None


@pytest.mark.parametrize("failure", [OSError, ValueError])
def test_unavailable_kernel_evidence_refuses_without_leaking_fds(tmp_path, monkeypatch, failure):
    before = set(Path("/proc/self/fd").iterdir())

    def fail(_descriptor):
        raise failure("unprovable")

    monkeypatch.setattr(native, "descriptor_mount_id", fail)
    assert native.linux_path_evidence(tmp_path, native.read_mountinfo()) is None
    assert set(Path("/proc/self/fd").iterdir()) == before


@pytest.mark.parametrize("info", ["", "mnt_id: wrong\n", "mnt_id: 1\nmnt_id: 2\n",
                                  "mnt_id: 1\n" + "x" * 4096])
def test_malformed_descriptor_mount_identity_refuses(monkeypatch, info):
    monkeypatch.setattr(Path, "open", lambda *args, **kwargs: StringIO(info))
    with pytest.raises(ValueError, match="mount identity"):
        native.descriptor_mount_id(123)
