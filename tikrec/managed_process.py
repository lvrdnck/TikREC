"""Linux process prerequisites for the dedicated managed-storage service."""

import ctypes
import os
from pathlib import Path
import sys

from .managed_paths import ProtectedPath


def verify_runtime(uid: int, code_directory: Path) -> None:
    """Require an isolated, unprivileged, non-login and administrator-owned runtime."""
    import pwd

    account = pwd.getpwuid(uid)
    if (uid == 0 or os.getuid() != uid or os.geteuid() != uid
            or Path(account.pw_shell).name not in {"nologin", "false"}
            or not sys.flags.isolated):
        raise ValueError("managed service requires its dedicated non-login UID and isolated Python")
    status = _status(Path("/proc/self/status"))
    if any(int(status[key], 16) for key in ("CapEff", "CapPrm", "CapAmb")):
        raise ValueError("managed service must have no process capabilities")
    libc = ctypes.CDLL(None, use_errno=True)
    # Suppress same-UID ptrace/fd access and privilege acquisition by children.
    if libc.prctl(4, 0, 0, 0, 0) or libc.prctl(38, 1, 0, 0, 0):
        raise OSError(ctypes.get_errno(), "could not constrain managed service process")
    if libc.prctl(3, 0, 0, 0, 0) != 0:
        raise ValueError("managed service process remains dumpable")
    module_root = Path(__file__).resolve().parent
    if module_root != code_directory / "tikrec":
        raise ValueError("managed code must run from the installed trusted package")
    paths = {code_directory, Path(sys.executable).resolve(), Path.cwd()}
    for entry in sys.path:
        path = Path(entry)
        if not path.is_absolute():
            raise ValueError("managed Python import path is relative")
        # An absent zip import slot is safe only under a protected ancestor.
        paths.add(path.resolve() if path.exists() else path.parent.resolve())
    for path in paths:
        held = ProtectedPath(path, 0, directory=path.is_dir())
        held.close()
    # A protected search directory alone does not exclude writes to existing
    # modules inside it. Validate loaded files and the installed package tree.
    for module in tuple(sys.modules.values()):
        filename = getattr(module, "__file__", None)
        if filename and Path(filename).exists():
            held = ProtectedPath(Path(filename).resolve(), 0, directory=False)
            held.close()
    for path in code_directory.rglob("*"):
        held = ProtectedPath(path.resolve(), 0, directory=path.is_dir())
        held.close()


def assert_quiescent_process(uid: int, root: Path) -> None:
    """Refuse another service-UID process, writable media descriptor, or mapping."""
    for entry in Path("/proc").iterdir():
        if not entry.name.isdecimal() or int(entry.name) == os.getpid():
            continue
        try:
            status = _status(entry / "status")
        except FileNotFoundError:
            continue  # A process that exited cannot retain a writable resource.
        except (OSError, ValueError) as error:
            raise ValueError("managed service process exclusion could not be proven") from error
        if uid in [int(value) for value in status["Uid"].split()]:
            raise ValueError("managed service has an unquiesced child or UID peer")
    prefix = str(root) + "/"
    for entry in Path("/proc/self/fd").iterdir():
        try:
            target = os.readlink(entry)
            flags = int(_status(Path("/proc/self/fdinfo") / entry.name)["flags"], 8)
        except FileNotFoundError:
            continue
        if (target.startswith(prefix) and flags & os.O_ACCMODE
                and target != str(root / ".tikrec-lifecycle.lock")):
            raise ValueError("managed media still has a writable descriptor")
    for line in Path("/proc/self/maps").read_text().splitlines():
        fields = line.split(maxsplit=5)
        if len(fields) == 6 and fields[5].startswith(prefix) and "w" in fields[1]:
            raise ValueError("managed media still has a writable mapping")


def _status(path: Path) -> dict:
    return dict(line.split(":", 1) for line in path.read_text().splitlines() if ":" in line)
