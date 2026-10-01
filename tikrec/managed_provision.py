"""Administrator-only creation of new managed storage; never adopt legacy media."""

import argparse
import grp
import json
import os
from pathlib import Path
import pwd
from uuid import uuid4

from .managed_paths import ProtectedPath
from .managed_storage import MARKER


def provision(base: Path, definition: Path, code: Path, *, user: str, reader_group: str) -> None:
    """Create fresh objects under protected ancestors and publish their genesis identity."""
    if os.geteuid() != 0:
        raise ValueError("managed storage provisioning requires the administrator")
    account, readers = pwd.getpwnam(user), grp.getgrnam(reader_group)
    if account.pw_uid == 0 or Path(account.pw_shell).name not in {"nologin", "false"}:
        raise ValueError("managed service requires a dedicated non-login account")
    if os.path.lexists(base) or os.path.lexists(definition):
        raise ValueError("managed provisioning refuses every existing base or definition")
    pins = []
    try:
        for path in (base.parent, definition.parent, code):
            pins.append(ProtectedPath(path, 0))
        # mkdir/O_EXCL refuse existing evidence. A failure preserves new partial
        # provisioning for administrator inspection; there is no cleanup/adoption.
        base.mkdir(mode=0o755)
        base.chmod(0o755)
        root, state = base / "recordings", base / "state"
        for directory in (root, state):
            directory.mkdir(mode=0o750)
            directory.chmod(0o750)
            os.chown(directory, account.pw_uid, readers.gr_gid)
        storage_id = str(uuid4())
        _write(root / MARKER, dict(schema_version=1, storage_id=storage_id,
                                  recording_root=str(root)), 0, readers.gr_gid, 0o440)
        _write(state / "config.json", dict(schema_version=1, output_directory=str(root)),
               account.pw_uid, readers.gr_gid, 0o640)
        _write(definition, dict(schema_version=1, service_uid=account.pw_uid,
                                storage_id=storage_id, recording_root=str(root),
                                state_directory=str(state), code_directory=str(code)),
               0, readers.gr_gid, 0o640)
        for directory in (root, state, base, base.parent, definition.parent):
            descriptor = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
    finally:
        while pins:
            pins.pop().close()


def _write(path, document, uid, gid, mode):
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        os.fchown(handle.fileno(), uid, gid)
        os.fchmod(handle.fileno(), mode)
        json.dump(document, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def main() -> None:
    """Provision a new dedicated root without deploying or starting a service."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, default=Path("/var/lib/tikrec"))
    parser.add_argument("--definition", type=Path, default=Path("/etc/tikrec/managed.json"))
    parser.add_argument("--code-directory", type=Path, required=True)
    parser.add_argument("--service-user", default="tikrec")
    parser.add_argument("--reader-group", default="tikrec-readers")
    args = parser.parse_args()
    provision(args.base, args.definition, args.code_directory,
              user=args.service_user, reader_group=args.reader_group)


if __name__ == "__main__":
    main()
