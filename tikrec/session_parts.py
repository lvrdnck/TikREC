"""Discover immutable writer parts and check framing without media subprocesses."""

from dataclasses import dataclass
from pathlib import Path
import re

from .flv import FlvFormatError
from .source import iter_tags
from .writer import _FLV_HEADER, _is_video_keyframe


@dataclass(frozen=True)
class RetainedParts:
    """Numerically ordered completed parts and the next unused writer index."""

    parts: tuple[Path, ...]
    next_index: int


def part_index(path: Path) -> int:
    """Accept only the positive index spelling emitted by the writer."""
    name = Path(path).name
    match = re.fullmatch(r"part-([0-9]+)\.flv", name)
    if match is None:
        raise ValueError("noncanonical retained part name")
    index = int(match.group(1))
    # Width four is a minimum, so 10000 is canonical but padded 00001 is not.
    if index < 1 or name != f"part-{index:04d}.flv":
        raise ValueError("noncanonical retained part name")
    return index


def part_order(path: Path) -> tuple[str, int, str, str]:
    """Order writer names numerically and other finalizer inputs deterministically."""
    path = Path(path)
    try:
        return "part-", part_index(path), path.name, str(path)
    except ValueError:
        # Manual finalize still accepts non-writer names; retain their lexical ordering.
        return path.name, 0, path.name, str(path)


def discover_parts(directory: Path) -> RetainedParts:
    """Require contiguous completed parts from one and refuse ambiguous artifacts."""
    directory = Path(directory)
    if not directory.is_dir() or directory.is_symlink():
        raise ValueError("resume requires an existing regular parts directory")
    parts = []
    for path in directory.iterdir():
        name = path.name.lower()
        if ".partial" in name:
            # A crash may have left media or JSON here; never promote, skip, or delete it.
            raise ValueError("partial artifact blocks resume; preserve evidence")
        if name.startswith(("part-", ".part-")) or name.endswith(".flv"):
            part_index(path)
            if not path.is_file() or path.is_symlink():
                raise ValueError("retained part must be a regular file")
            parts.append(path)
        # Non-part, non-FLV, non-partial files cannot claim a writer index and are ignored.
    ordered = tuple(sorted(parts, key=part_order))
    if not ordered:
        raise ValueError("resume requires completed parts; no completed parts found")
    for expected, path in enumerate(ordered, 1):
        if part_index(path) != expected:
            raise ValueError("retained parts must be contiguous from part-0001.flv")
        _check_structure(path)
    return RetainedParts(ordered, len(ordered) + 1)


def _check_structure(path: Path) -> None:
    try:
        with path.open("rb") as handle:
            # Retained TikREC parts always use this header, including video-only captures.
            if handle.read(len(_FLV_HEADER)) != _FLV_HEADER:
                raise ValueError("part has a non-writer FLV header")
            handle.seek(0)
            tags = iter_tags(iter(lambda: handle.read(64 * 1024), b""))
            first = next(tags, None)
            if first is None or not first.is_avc_configuration or len(first.payload) < 6:
                raise ValueError("part must begin with its own AVC sequence header")
            has_media = has_audio_config = False
            for tag in tags:
                if tag.tag_type == 8 and tag.is_configuration:
                    has_audio_config = True
                if tag.is_avc_configuration and tag.payload[5:] != first.payload[5:]:
                    raise ValueError("part contains a changed AVC configuration")
                if tag.is_media:
                    if not has_media and (not _is_video_keyframe(tag) or tag.timestamp != 0):
                        raise ValueError("part must start media at its own rebased keyframe")
                    if tag.tag_type == 8 and not has_audio_config:
                        raise ValueError("audio media lacks its own sequence header")
                    has_media = True
            if not has_media:
                raise ValueError("part contains no decodable-start media")
    except (OSError, EOFError, FlvFormatError, ValueError) as error:
        # Framing proves only structural suitability, never actual codec decode health.
        raise ValueError(f"retained part failed structural checks: {path.name}") from error
