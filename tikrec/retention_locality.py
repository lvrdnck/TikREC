"""Conservative local-volume identity for read-only retention eligibility."""

from __future__ import annotations

import ctypes
import os
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


@dataclass(frozen=True)
class _LinuxMount:
    ident: str
    parent: str
    device: tuple[int, int]
    point: PurePosixPath
    kind: str


def proven_local(path: Path, *, platform_name: str | None = None,
                 windows_drive_type=None, linux_mountinfo: str | None = None,
                 mac_mounts: str | None = None,
                 actual_device: tuple[int, int] | None = None) -> bool:
    """Say whether complete platform evidence proves a supported local volume."""
    return local_volume(path, platform_name=platform_name,
                        windows_drive_type=windows_drive_type,
                        linux_mountinfo=linux_mountinfo, mac_mounts=mac_mounts,
                        actual_device=actual_device) is not None


def local_volume(path: Path, *, platform_name: str | None = None,
                 windows_drive_type=None, linux_mountinfo: str | None = None,
                 mac_mounts: str | None = None,
                 actual_device: tuple[int, int] | None = None) -> LocalVolume | None:
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
            mounts.append(_LinuxMount(fields[0], fields[1],
                                      tuple(map(int, fields[2].split(":"))),
                                      PurePosixPath(point), detail[0]))
        return _linux_volume(path, mounts, actual_device)
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


def _linux_volume(path: Path, mounts: list[_LinuxMount],
                  actual_device: tuple[int, int] | None) -> LocalVolume | None:
    """Require the selected local mount to follow the visible covering ancestry."""
    target = PurePosixPath(str(path))
    matching = [mount for mount in mounts
                if target == mount.point or mount.point in target.parents]
    if not matching or len({mount.ident for mount in mounts}) != len(mounts):
        return None
    by_id = {mount.ident: mount for mount in mounts}
    deepest = max(len(mount.point.parts) for mount in matching)
    selected = [mount for mount in matching if len(mount.point.parts) == deepest]
    if len(selected) != 1 or selected[0].kind.lower() not in _LOCAL_FILESYSTEMS:
        return None
    # The parent chain must contain every visible covering mount. A lexical local
    # child with a different parent is hidden by an intervening remote overmount.
    current = selected[0]
    visited = set()
    ancestors = set()
    while current.parent in by_id:
        if current.ident in visited:
            return None
        visited.add(current.ident)
        parent = by_id[current.parent]
        if parent.point != current.point and parent.point not in current.point.parents:
            return None
        ancestors.add(parent.ident)
        current = parent
    # Namespace roots can name a parent outside the visible mount table.
    if current.point != PurePosixPath("/"):
        return None
    if any(mount.ident != selected[0].ident and mount.ident not in ancestors
           for mount in matching):
        return None
    if actual_device is None and sys.platform.startswith("linux") and isinstance(path, Path):
        try:
            actual = path.stat().st_dev
            actual_device = (os.major(actual), os.minor(actual))
        except (OSError, ValueError):
            return None
    if actual_device is not None and selected[0].device != actual_device:
        return None
    return LocalVolume("linux", str(selected[0].point), selected[0].ident)
