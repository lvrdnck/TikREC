"""Platform-specific location of the per-user TikREC configuration file."""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path, PurePosixPath


def default_config_path(*, os_name: str | None = None,
                        environ: Mapping[str, str] | None = None,
                        home: Path | None = None) -> Path:
    """Return the deterministic platform configuration path for the current user."""
    platform = os.name if os_name is None else os_name
    variables = os.environ if environ is None else environ
    user_home = Path.home() if home is None else Path(home)
    if platform == "nt":
        base = Path(variables.get("APPDATA") or user_home / "AppData" / "Roaming")
    else:
        configured_base = variables.get("XDG_CONFIG_HOME")
        # XDG requires an absolute value; ignore invalid overrides.
        base = (Path(configured_base)
                if configured_base and PurePosixPath(configured_base).is_absolute()
                else user_home / ".config")
    return base / "TikREC" / "config.json"
