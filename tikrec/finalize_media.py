"""Shared media-only planning helpers; execution and publication belong to callers."""

from collections.abc import Iterable, Iterator
from fractions import Fraction
from pathlib import Path
from tempfile import NamedTemporaryFile

from .flv import FlvFormatError
from .source import iter_tags
from .session_parts import part_order


def _validate_parts(parts: Iterable[Path]) -> tuple[Path, ...]:
    # Four-digit padding is a minimum; lexical sorting misorders part 10000 before 9999.
    ordered_parts = tuple(
        sorted((Path(part) for part in parts), key=part_order)
    )
    if not ordered_parts:
        raise ValueError("at least one completed FLV part is required")
    for part in ordered_parts:
        if not part.is_file():
            raise FileNotFoundError(f"completed FLV part is missing: {part}")
    return ordered_parts


def _validate_output_path(output_path: Path) -> None:
    if not output_path.parent.is_dir():
        raise ValueError(f"output directory does not exist: {output_path.parent}")
    if output_path.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {output_path}")
    if not output_path.suffix:
        raise ValueError("output path must have a container extension")


def _temporary_output_path(output_path: Path) -> Path:
    """Return a hidden temporary path that retains FFmpeg's output suffix."""
    suffix = output_path.suffix
    stem = output_path.name[: -len(suffix)]
    # FFmpeg chooses its muxer from the last suffix, so ``.partial`` belongs
    # before it rather than after it. Keeping the directory unchanged permits
    # ``os.replace`` to remain atomic on filesystems that support it.
    return output_path.with_name(f".{stem}.partial{suffix}")


def _configuration_for(part: Path) -> bytes:
    try:
        for tag in iter_tags(_file_chunks(part)):
            if tag.is_avc_configuration:
                return tag.payload[5:]
    except (EOFError, FlvFormatError) as error:
        raise ValueError(f"invalid completed FLV part {part}: {error}") from error
    raise ValueError(f"completed FLV part has no AVC configuration: {part}")


def _file_chunks(path: Path, chunk_size: int = 64 * 1024) -> Iterator[bytes]:
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            yield chunk


def _write_concat_manifest(parts: tuple[Path, ...], directory: Path) -> Path:
    with NamedTemporaryFile(
        mode="w", encoding="utf-8", suffix=".ffconcat", prefix=".tikrec-", dir=directory,
        delete=False,
    ) as handle:
        for part in parts:
            handle.write(f"file {_concat_path(part.resolve())}\n")
        return Path(handle.name)


def _concat_path(path: Path) -> str:
    # The concat demuxer uses single quotes; escape them without invoking a shell.
    return "'" + str(path).replace("'", r"'\''") + "'"


def _build_ffmpeg_command(
    parts: tuple[Path, ...],
    temporary_output: Path,
    *,
    ffmpeg: str | Path,
    manifest: Path | None,
    target_size: tuple[int, int] | None,
    nominal_rate: Fraction | None = None,
) -> list[str]:
    command = [str(ffmpeg), "-nostdin", "-n"]
    if manifest is not None:
        return command + [
            "-f", "concat", "-safe", "0", "-i", str(manifest),
            "-map", "0", "-c", "copy", "-movflags", "+faststart", str(temporary_output),
        ]

    assert target_size is not None
    assert nominal_rate is not None
    for part in parts:
        command.extend(["-i", str(part)])
    command.extend([
        "-filter_complex", _concat_filter(len(parts), target_size),
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-c:a", "aac", "-movflags", "+faststart",
        # x264's nominal rate affects level selection, not frame timestamps.
        "-x264-params", f"fps={nominal_rate.numerator}/{nominal_rate.denominator}",
        # Preserve irregular frame intervals instead of rounding onto a nominal CFR grid.
        "-fps_mode:v", "passthrough", "-enc_time_base:v", "filter",
        str(temporary_output),
    ])
    return command


def _concat_filter(part_count: int, target_size: tuple[int, int]) -> str:
    width, height = target_size
    filters = []
    for index in range(part_count):
        # Reset every part independently before concat; otherwise rebased FLV
        # timestamps can leave a gap or push audio away from its video segment.
        filters.append(
            f"[{index}:v:0]scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1,setpts=PTS-STARTPTS[v{index}]"
        )
        filters.append(f"[{index}:a:0]asetpts=PTS-STARTPTS[a{index}]")
    inputs = "".join(f"[v{index}][a{index}]" for index in range(part_count))
    filters.append(f"{inputs}concat=n={part_count}:v=1:a=1[v][a]")
    return ";".join(filters)


def progress_command(command: list[str], enabled: bool) -> list[str]:
    """Use the existing structured stderr progress flags only when requested."""
    return command[:2] + [
        "-progress", "pipe:2", "-nostats", "-loglevel", "warning",
    ] + command[2:] if enabled else command


