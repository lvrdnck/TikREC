"""Optional output inspection keeps the manifest's media shape stable."""

from tikrec.manifest_media import media_values
from tikrec.media import MediaInfo


def test_missing_media_keeps_all_optional_facts_null():
    assert media_values(None) == {
        "video_codec": None, "audio_codec": None, "width": None, "height": None,
    }
    assert media_values(MediaInfo("h264", "aac", 720, 1280))["width"] == 720
