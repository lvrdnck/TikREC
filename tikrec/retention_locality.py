"""Prove that an advisory retention root is on known local storage."""

from __future__ import annotations

import ctypes
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath


_LOCAL_FILESYSTEMS = {"apfs", "hfs", "hfsplus", "ext2", "ext3", "ext4", "xfs",
                      "btrfs", "zfs", "f2fs", "tmpfs", "ntfs", "vfat", "exfat"}


def proven_local(path: Path, *, platform_name: str | None = None,
                 windows_drive_type=None, linux_mountinfo: str | None = None,
                 mac_mounts: str | None = None) -> bool:
    """Fail closed when platform mount evidence cannot prove a local volume."""
    platform_name = sys.platform if platform_name is None else platform_name
    if platform_name == "win32":
        try:
            drive_type = windows_drive_type or ctypes.windll.kernel32.GetDriveTypeW
            return drive_type(str(path.anchor)) == 3  # DRIVE_FIXED; mapped drives report REMOTE.
        except (OSError, AttributeError, ValueError):
            return False
    if platform_name.startswith("linux"):
        if linux_mountinfo is None:
            try:
                with Path("/proc/self/mountinfo").open(encoding="utf-8") as handle:
                    linux_mountinfo = handle.read(1_000_001)
            except OSError:
                return False
            if len(linux_mountinfo) > 1_000_000:
                return False
        mounts = []
        for line in linux_mountinfo.splitlines():
            left, separator, right = line.partition(" - ")
            fields = left.split()
            if separator and len(fields) >= 5 and right.split():
                point = re.sub(r"\\([0-7]{3})", lambda match: chr(int(match[1], 8)), fields[4])
                mounts.append((point, right.split()[0]))
        return _known_local_mount(path, mounts)
    if platform_name == "darwin":
        if mac_mounts is None:
            try:
                result = subprocess.run(["/sbin/mount"], capture_output=True, text=True, timeout=2)
            except (OSError, subprocess.TimeoutExpired):
                return False
            if result.returncode or len(result.stdout) > 1_000_000:
                return False
            mac_mounts = result.stdout
        mounts = []
        for line in mac_mounts.splitlines():
            match = re.search(r" on (.+?) \(([^, )]+)", line)
            if match:
                mounts.append((match[1], match[2]))
        return _known_local_mount(path, mounts)
    return False


def _known_local_mount(path: Path, mounts: list[tuple[str, str]]) -> bool:
    target = PurePosixPath(str(path))
    selected = max(((point, kind) for point, kind in mounts
                    if target == PurePosixPath(point) or PurePosixPath(point) in target.parents),
                   key=lambda pair: len(pair[0]), default=None)
    return selected is not None and selected[1].lower() in _LOCAL_FILESYSTEMS
