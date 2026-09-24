"""Conservative local-volume identity for read-only retention eligibility."""

from __future__ import annotations

import ctypes
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath


_LOCAL_FILESYSTEMS = {"apfs", "hfs", "hfsplus", "ext2", "ext3", "ext4", "xfs",
                      "btrfs", "zfs", "f2fs", "tmpfs", "ntfs", "vfat", "exfat"}
_MOUNT_ESCAPE = re.compile(r"\\([0-7]{3})")


@dataclass(frozen=True)
class LocalVolume:
    """One proven local drive or unambiguous mount identity."""

    platform: str
    point: str
    identity: str


def proven_local(path: Path, *, platform_name: str | None = None,
                 windows_drive_type=None, linux_mountinfo: str | None = None,
                 mac_mounts: str | None = None) -> bool:
    """Say whether complete platform evidence proves a supported local volume."""
    return local_volume(path, platform_name=platform_name,
                        windows_drive_type=windows_drive_type,
                        linux_mountinfo=linux_mountinfo, mac_mounts=mac_mounts) is not None


def local_volume(path: Path, *, platform_name: str | None = None,
                 windows_drive_type=None, linux_mountinfo: str | None = None,
                 mac_mounts: str | None = None) -> LocalVolume | None:
    """Identify the deepest unambiguous local mount or fixed Windows drive."""
    platform_name = sys.platform if platform_name is None else platform_name
    if platform_name == "win32":
        try:
            drive_type = windows_drive_type or ctypes.windll.kernel32.GetDriveTypeW
            anchor = str(path.anchor)
            return (LocalVolume("win32", anchor.casefold(), anchor.casefold())
                    if anchor and drive_type(anchor) == 3 else None)
        except (OSError, AttributeError, ValueError):
            return None
    if platform_name.startswith("linux"):
        if linux_mountinfo is None:
            try:
                with Path("/proc/self/mountinfo").open(encoding="utf-8") as handle:
                    linux_mountinfo = handle.read(1_000_001)
            except OSError:
                return None
        if len(linux_mountinfo) > 1_000_000:
            return None
        mounts = []
        for line in linux_mountinfo.splitlines():
            if not line.strip():
                continue
            left, separator, right = line.partition(" - ")
            fields, detail = left.split(), right.split()
            if (not separator or len(fields) < 6 or len(detail) < 3
                    or not fields[0].isdigit() or not fields[1].isdigit()
                    or not re.fullmatch(r"[0-9]+:[0-9]+", fields[2])
                    or not fields[4].startswith("/")):
                return None
            point = _MOUNT_ESCAPE.sub(lambda match: chr(int(match[1], 8)), fields[4])
            if "\\" in point or not point.startswith("/"):
                return None
            mounts.append((point, detail[0], fields[0]))
        return _selected_volume(path, mounts, "linux")
    if platform_name == "darwin":
        if mac_mounts is None:
            try:
                result = subprocess.run(["/sbin/mount"], capture_output=True, text=True, timeout=2)
            except (OSError, subprocess.TimeoutExpired):
                return None
            if result.returncode or len(result.stdout) > 1_000_000:
                return None
            mac_mounts = result.stdout
        mounts = []
        for line in mac_mounts.splitlines():
            if not line.strip():
                continue
            match = re.fullmatch(r".+ on (/.+|/) \(([^, )]+)(?:,.*)?\)", line)
            if match is None:
                return None
            mounts.append((match[1], match[2], match[1]))
        return _selected_volume(path, mounts, "darwin")
    return None


def _selected_volume(path: Path, mounts: list[tuple[str, str, str]],
                     platform: str) -> LocalVolume | None:
    """Reject unknown, remote, or equally deep stacked mounts."""
    target = PurePosixPath(str(path))
    matching = [(PurePosixPath(point), kind, identity) for point, kind, identity in mounts
                if target == PurePosixPath(point) or PurePosixPath(point) in target.parents]
    if not matching:
        return None
    depth = max(len(point.parts) for point, _, _ in matching)
    selected = [mount for mount in matching if len(mount[0].parts) == depth]
    if len(selected) != 1 or selected[0][1].lower() not in _LOCAL_FILESYSTEMS:
        return None
    point, _, identity = selected[0]
    return LocalVolume(platform, str(point), identity)
