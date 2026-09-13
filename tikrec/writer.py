"""Write an iterable of FLV tags into independently decodable FLV parts."""

from __future__ import annotations

import os
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import BinaryIO

from .flv import FLV_AUDIO_TAG, FlvTag
from .flv_codec import avc_configuration_facts
from .flv_metadata import metadata_frame_rate
from .writer_events import (PartTiming, TimestampReplay, _PendingTimestampReplay,
                            _observe_timestamp, _finish_timestamp_replay)


# The flags byte advertises both audio and video; TikTok parts can contain both.
_FLV_HEADER = b"FLV\x01\x05\x00\x00\x00\x09\x00\x00\x00\x00"


def write_parts(
    tags: Iterable[FlvTag],
    output_dir: Path,
    *,
    start_index: int = 1,
    on_part_started: Callable[[Path], None] | None = None,
    on_progress: Callable[[Path, int], None] | None = None,
    on_part_retained: Callable[[Path], None] | None = None,
    on_part_closed: Callable[[PartTiming], None] | None = None,
    on_timestamp_replay: Callable[[TimestampReplay], None] | None = None,
    on_media_retained: Callable[[], None] | None = None,
) -> tuple[Path, ...]:
    """Write media into numbered FLV parts and return the retained paths.

    ``start_index`` is a positive integer, default one; each call owns fresh
    codec/keyframe/timestamp state independently of previous calls.
    ``on_part_started`` fires when a keyframe makes a part decodable.
    ``on_progress`` receives the active part's final name and written bytes.
    ``on_part_closed`` receives original source timestamps for each retained
    part, before timestamp rebasing makes its keyframe-gate interval opaque.
    ``on_timestamp_replay`` receives completed backward-clock intervals without
    suppressing any of their source tags.
    ``on_media_retained`` fires only after an audio/video media tag is written,
    excluding configuration tags and media discarded by the keyframe gate.
    """
    # bool is an int subclass, but it is not an intentional part allocation index.
    if type(start_index) is not int or start_index < 1:
        raise ValueError("start_index must be a positive integer")
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    part: _OpenPart | None = None
    configuration: bytes | None = None
    latest_audio_configuration: FlvTag | None = None
    metadata_rate: str | None = None

    try:
        for tag in tags:
            if tag.tag_type == 18:
                # Inspect script metadata without changing whether the writer retains it.
                rate = metadata_frame_rate(tag.payload)
                if rate is not None:
                    metadata_rate = rate
                    # Metadata can announce the next config; do not relabel a started part.
                    if part is not None and (not part.started or part.metadata_rate is None):
                        part.metadata_rate = rate
            if tag.tag_type == FLV_AUDIO_TAG and tag.is_configuration:
                latest_audio_configuration = tag
                if part is not None and part.started:
                    # An AAC sequence header changes decoder state for packets
                    # that follow it, so retain it at its incoming timestamp.
                    _write_tag(part, tag, on_timestamp_replay=on_timestamp_replay)
                    _report_progress(part, on_progress)
                continue

            if tag.is_avc_configuration:
                # AVC video tags have a one-byte video header and three-byte
                # composition time before the decoder-configuration record.
                next_configuration = tag.payload[5:]
                if configuration != next_configuration:
                    _close_part(part, paths, on_part_retained, on_part_closed, on_timestamp_replay)
                    part = None
                    part = _open_part(output_dir, start_index + len(paths), tag)
                    part.metadata_rate = metadata_rate
                    configuration = next_configuration
                    continue

                if part is not None and part.started:
                    _write_tag(part, tag, on_timestamp_replay=on_timestamp_replay)
                    _report_progress(part, on_progress)
                elif part is not None:
                    # Keep the latest repeated sequence header until its keyframe;
                    # it is the configuration that belongs with the new rendition.
                    part.configuration_tag = tag
                continue

            if part is None:
                continue

            if tag.is_media and part.first_media_timestamp is None:
                # Sequence headers can use a different clock origin, unlike media.
                part.first_media_timestamp = tag.timestamp

            if not part.started:
                if not _is_video_keyframe(tag):
                    continue
                part.base_timestamp = tag.timestamp
                part.first_keyframe_timestamp = tag.timestamp
                _write_tag(part, part.configuration_tag, observe_timestamp=False, on_timestamp_replay=on_timestamp_replay)
                if latest_audio_configuration is not None:
                    _write_tag(part, latest_audio_configuration, observe_timestamp=False, on_timestamp_replay=on_timestamp_replay)
                part.started = True
                if on_part_started is not None:
                    on_part_started(part.final_path)

            _write_tag(part, tag, on_timestamp_replay=on_timestamp_replay)
            if tag.is_media and on_media_retained is not None:
                on_media_retained()
            _report_progress(part, on_progress)
    finally:
        # Iteration can be interrupted by Ctrl-C or a malformed source. Close
        # the active file before exposing the exception to the capture layer.
        _close_part(part, paths, on_part_retained, on_part_closed, on_timestamp_replay)
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
        self.configuration_timestamp = configuration_tag.timestamp
        self.first_media_timestamp: int | None = None
        self.first_keyframe_timestamp: int | None = None
        self.last_tag_timestamp: int | None = None
        self.base_timestamp = 0
        self.started = False
        self.media_tag_count = 0
        self.tag_position = 0
        self.last_observed_timestamps: dict[int, int] = {}
        self.pending_replays: dict[int, _PendingTimestampReplay] = {}
        self.timestamp_replays: list[TimestampReplay] = []
        self.closed = False
        self.metadata_rate: str | None = None


def _open_part(output_dir: Path, index: int, configuration_tag: FlvTag) -> _OpenPart:
    final_path = output_dir / f"part-{index:04d}.flv"
    partial_path = output_dir / f".{final_path.name}.partial"
    if final_path.exists() or final_path.is_symlink() or partial_path.exists():
        raise FileExistsError(f"refusing to overwrite {final_path}")
    handle = partial_path.open("xb")
    handle.write(_FLV_HEADER)
    return _OpenPart(handle, partial_path, final_path, configuration_tag)


def _write_tag(part: _OpenPart, tag: FlvTag, *, observe_timestamp: bool = True, on_timestamp_replay: Callable[[TimestampReplay], None] | None = None) -> None:
    part.tag_position += 1
    if observe_timestamp and tag.is_media:
        _observe_timestamp(part, tag, on_timestamp_replay)
    part.handle.write(tag.encoded(base_timestamp=part.base_timestamp))
    part.last_tag_timestamp = tag.timestamp
    if tag.is_media:
        part.media_tag_count += 1


def _report_progress(
    part: _OpenPart,
    on_progress: Callable[[Path, int], None] | None,
) -> None:
    if on_progress is not None:
        on_progress(part.final_path, part.handle.tell())


def _close_part(
    part: _OpenPart | None,
    paths: list[Path],
    on_part_retained: Callable[[Path], None] | None,
    on_part_closed: Callable[[PartTiming], None] | None,
    on_timestamp_replay: Callable[[TimestampReplay], None] | None,
) -> None:
    if part is None or part.closed:
        return
    part.handle.close()
    part.closed = True
    for stream in tuple(part.pending_replays):
        _finish_timestamp_replay(part, stream, recovered=False, callback=on_timestamp_replay)
    if part.media_tag_count == 0:
        part.partial_path.unlink()
        return
    # Rename only a closed file so consumers never see a still-growing part.
    if part.final_path.exists() or part.final_path.is_symlink():
        # A collision discovered after opening must preserve both media artifacts.
        raise FileExistsError(f"refusing to overwrite {part.final_path}")
    os.replace(part.partial_path, part.final_path)
    paths.append(part.final_path)
    if on_part_retained is not None:
        on_part_retained(part.final_path)
    assert part.first_keyframe_timestamp is not None
    assert part.first_media_timestamp is not None
    assert part.last_tag_timestamp is not None
    if on_part_closed is not None:
        # Codec-header diagnostics avoid a subprocess delay on the reconnect path.
        width, height, rate = avc_configuration_facts(part.configuration_tag.payload[5:])
        nominal_rate = part.metadata_rate or rate
        rate_source = "onMetaData" if part.metadata_rate else "sps_vui" if rate else None
        on_part_closed(PartTiming(
            part.final_path,
            part.configuration_timestamp,
            part.first_media_timestamp,
            part.first_keyframe_timestamp,
            part.last_tag_timestamp,
            tuple(part.timestamp_replays),
            width, height, nominal_rate, rate_source,
        ))


def _is_video_keyframe(tag: FlvTag) -> bool:
    return (
        tag.is_media
        and tag.tag_type == 9
        and bool(tag.payload)
        and tag.payload[0] >> 4 == 1
    )
