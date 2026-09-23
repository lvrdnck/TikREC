"""No-follow local path boundary for read-only retention inspection."""

from __future__ import annotations

import os
import stat
from pathlib import Path


_REPARSE_POINT = 0x400


def local_path(path: Path, *, directory: bool) -> Path:
    """Return an absolute local path only when no existing component redirects."""
    value = Path(os.path.abspath(path))
    if str(value).startswith("\\\\"):
        raise ValueError("retention requires local storage")
    for component in (*reversed(value.parents), value):
        details = component.lstat()
        if (stat.S_ISLNK(details.st_mode)
                or getattr(details, "st_file_attributes", 0) & _REPARSE_POINT):
            raise ValueError("retention path redirects outside its local scope")
    details = value.lstat()
    if directory and not stat.S_ISDIR(details.st_mode):
        raise ValueError("retention path is not a regular directory")
    if not directory and not stat.S_ISREG(details.st_mode):
        raise ValueError("retention output is not a regular file")
    return value
