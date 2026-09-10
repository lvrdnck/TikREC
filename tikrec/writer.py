"""Write an iterable of FLV tags into independently decodable FLV parts."""

from __future__ import annotations

import os
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import BinaryIO

from .flv import FLV_AUDIO_TAG, FlvTag


# The flags byte advertises both audio and video; TikTok parts can contain both.
_FLV_HEADER = b"FLV\x01\x05\x00\x00\x00\x09\x00\x00\x00\x00"


def write_parts(
    tags: Iterable[FlvTag],
    output_dir: Path,
    *,
    start_index: int = 1,
    on_part_retained: Callable[[Path], None] | None = None,
) -> tuple[Path, ...]:
    """Write media into numbered FLV parts and return the retained paths."""
    if not isinstance(start_index, int) or start_index < 1:
        raise ValueError("start_index must be a positive integer")
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    part: _OpenPart | None = None
    configuration: bytes | None = None
    latest_audio_configuration: FlvTag | None = None

    try:
        for tag in tags:
            if tag.tag_type == FLV_AUDIO_TAG and tag.is_configuration:
                latest_audio_configuration = tag
                if part is not None and part.started:
                    # An AAC sequence header changes decoder state for packets
                    # that follow it, so retain it at its incoming timestamp.
                    _write_tag(part, tag)
                continue

            if tag.is_avc_configuration:
                # AVC video tags have a one-byte video header and three-byte
                # composition time before the decoder-configuration record.
                next_configuration = tag.payload[5:]
                if configuration != next_configuration:
                    _close_part(part, paths, on_part_retained)
                    part = None
                    part = _open_part(output_dir, start_index + len(paths), tag)
                    configuration = next_configuration
                    continue

                if part is not None and part.started:
                    _write_tag(part, tag)
                elif part is not None:
                    # Keep the latest repeated sequence header until its keyframe;
                    # it is the configuration that belongs with the new rendition.
                    part.configuration_tag = tag
                continue

            if part is None:
                continue

            if not part.started:
                if not _is_video_keyframe(tag):
                    continue
                part.base_timestamp = tag.timestamp
                _write_tag(part, part.configuration_tag)
                if latest_audio_configuration is not None:
                    _write_tag(part, latest_audio_configuration)
                part.started = True

            _write_tag(part, tag)
    finally:
        # Iteration can be interrupted by Ctrl-C or a malformed source. Close
        # the active file before exposing the exception to the capture layer.
        _close_part(part, paths, on_part_retained)
    return tuple(paths)


class _OpenPart:
    """The temporary file and state for one pending output part."""

    def __init__(
        self,
        handle: BinaryIO,
        partial_path: Path,
        final_path: Path,
        configuration_tag: FlvTag,
    ) -> None:
        self.handle = handle
        self.partial_path = partial_path
        self.final_path = final_path
        self.configuration_tag = configuration_tag
        self.base_timestamp = 0
        self.started = False
        self.media_tag_count = 0
        self.closed = False


def _open_part(output_dir: Path, index: int, configuration_tag: FlvTag) -> _OpenPart:
    final_path = output_dir / f"part-{index:04d}.flv"
    partial_path = output_dir / f".{final_path.name}.partial"
    if final_path.exists() or partial_path.exists():
        raise FileExistsError(f"refusing to overwrite {final_path}")
    handle = partial_path.open("xb")
    handle.write(_FLV_HEADER)
    return _OpenPart(handle, partial_path, final_path, configuration_tag)


def _write_tag(part: _OpenPart, tag: FlvTag) -> None:
    part.handle.write(tag.encoded(base_timestamp=part.base_timestamp))
    if tag.is_media:
        part.media_tag_count += 1


def _close_part(
    part: _OpenPart | None,
    paths: list[Path],
    on_part_retained: Callable[[Path], None] | None,
) -> None:
    if part is None or part.closed:
        return
    part.handle.close()
    part.closed = True
    if part.media_tag_count == 0:
        part.partial_path.unlink()
        return
    # Rename only a closed file so consumers never see a still-growing part.
    os.replace(part.partial_path, part.final_path)
    paths.append(part.final_path)
    if on_part_retained is not None:
        on_part_retained(part.final_path)


def _is_video_keyframe(tag: FlvTag) -> bool:
    return (
        tag.is_media
        and tag.tag_type == 9
        and bool(tag.payload)
        and tag.payload[0] >> 4 == 1
    )
