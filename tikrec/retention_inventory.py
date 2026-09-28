"""Conservative advisory byte and file counts for retention planning."""

from __future__ import annotations

import re
from pathlib import Path

from .retention_authorization import fingerprint


_PART_NAME = re.compile(r"part-[0-9]+\.flv\Z")
_UNKNOWN = {"file_count": None, "flv_part_count": None,
            "final_output_bytes": None, "retained_parts_bytes": None,
            "total_file_bytes": None}


def unknown_inventory() -> dict[str, int | None]:
    """Return explicit unknowns rather than implying that absent proof is zero."""
    return dict(_UNKNOWN)


def inspect_inventory(root: Path, parts: Path, output_path: str | None,
                      volume) -> dict[str, int | None]:
    """Count only stable, singly linked regular files on the proven local volume."""
    if output_path is None:
        return unknown_inventory()
    output = Path(output_path)
    try:
        before_directory = fingerprint(root, parts, directory=True, volume=volume)
        names = tuple(sorted(parts.iterdir(), key=lambda path: path.name))
        before = tuple(fingerprint(root, path, directory=False, volume=volume)
                       for path in names)
        before_output = fingerprint(root, output, directory=False, volume=volume)
        # The inventory is advisory, but every displayed size needs a stable
        # no-follow observation across the complete enumeration.
        after = tuple(fingerprint(root, path, directory=False, volume=volume)
                      for path in names)
        if (before != after or before_output != fingerprint(
                root, output, directory=False, volume=volume)
                or before_directory != fingerprint(root, parts, directory=True,
                                                 volume=volume)
                or names != tuple(sorted(parts.iterdir(), key=lambda path: path.name))):
            return unknown_inventory()
        retained = sum(item.size for item in before)
        return {"file_count": len(before) + 1,
                "flv_part_count": sum(bool(_PART_NAME.fullmatch(path.name))
                                      for path in names),
                "final_output_bytes": before_output.size,
                "retained_parts_bytes": retained,
                "total_file_bytes": retained + before_output.size}
    except (OSError, ValueError, TypeError):
        return unknown_inventory()
