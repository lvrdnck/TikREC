"""Optional media metadata stored alongside the session lifecycle."""

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
