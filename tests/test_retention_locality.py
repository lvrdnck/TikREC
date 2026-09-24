"""Deterministic local-volume evidence for read-only retention scope."""

from pathlib import PurePosixPath

import pytest

from tikrec.retention_locality import proven_local


@pytest.mark.parametrize("drive_type,expected", [(3, True), (4, False),
                                                  (0, False), (1, False), (2, False)])
def test_windows_drive_classification_is_fail_closed(tmp_path, drive_type, expected):
    assert proven_local(tmp_path, platform_name="win32",
                        windows_drive_type=lambda _: drive_type) is expected


@pytest.mark.parametrize("kind,expected", [("ext4", True), ("cifs", False),
                                             ("nfs4", False), ("overlay", False),
                                             ("mysteryfs", False)])
def test_linux_mount_classification_is_fail_closed(kind, expected):
    mounts = f"1 0 0:1 / / rw - {kind} device rw\n"
    assert proven_local(PurePosixPath("/recordings"), platform_name="linux",
                        linux_mountinfo=mounts) is expected


def test_deeper_remote_mount_overrides_local_parent():
    mounts = ("1 0 0:1 / / rw - ext4 local rw\n"
              "2 1 0:2 / /recordings rw - cifs server rw\n")
    assert not proven_local(PurePosixPath("/recordings/session"), platform_name="linux",
                            linux_mountinfo=mounts)


@pytest.mark.parametrize("kind,expected", [("apfs", True), ("smbfs", False),
                                             ("unknownfs", False)])
def test_macos_mount_classification_is_fail_closed(kind, expected):
    mounts = f"/dev/disk1 on / ( {kind}, local)\n".replace("( ", "(")
    assert proven_local(PurePosixPath("/recordings"), platform_name="darwin",
                        mac_mounts=mounts) is expected


def test_unsupported_platform_cannot_prove_locality():
    assert not proven_local(PurePosixPath("/recordings"), platform_name="unknown")


def test_malformed_deeper_mount_cannot_fall_back_to_local_parent():
    mounts = ("1 0 0:1 / / rw - ext4 local rw\n"
              "2 1 0:2 / /recordings rw -\n")
    assert not proven_local(PurePosixPath("/recordings/session"), platform_name="linux",
                            linux_mountinfo=mounts)


def test_stacked_same_path_mount_is_ambiguous():
    mounts = ("1 0 0:1 / / rw - ext4 local rw\n"
              "2 1 0:2 / /recordings rw - ext4 local rw\n"
              "3 2 0:3 / /recordings rw - nfs server rw\n")
    assert not proven_local(PurePosixPath("/recordings/session"), platform_name="linux",
                            linux_mountinfo=mounts)


def test_malformed_macos_mount_cannot_fall_back_to_local_parent():
    mounts = "/dev/disk1 on / (apfs, local)\ninvalid mount line\n"
    assert not proven_local(PurePosixPath("/recordings"), platform_name="darwin",
                            mac_mounts=mounts)
