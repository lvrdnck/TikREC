"""Optional media metadata stored alongside the session lifecycle."""

from pathlib import Path

from .media import MediaInfo


def media_values(info: MediaInfo | None) -> dict[str, str | int | None]:
    """Keep the manifest media object stable when inspection is unavailable."""
    info = info or MediaInfo()
    return {
        "video_codec": info.video_codec,
        "audio_codec": info.audio_codec,
        "width": info.width,
        "height": info.height,
    }


def inspect_output(values: dict, output_path: Path | None, inspector) -> None:
    """Keep optional media inspection from changing session completion."""
    media_path = Path(output_path) if output_path is not None else None
    if media_path is None or not media_path.is_file():
        return
    try:
        values["media"] = media_values(inspector(media_path))
    except Exception:
        values["media"] = media_values(None)
