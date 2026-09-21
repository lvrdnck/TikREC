"""Offline safety tests for explicit and automatic local recording paths."""

import json
from datetime import datetime
from pathlib import Path

import pytest

from tikrec.configuration import ConfigurationError
from tikrec.output_naming import local_recording_paths, safe_creator_handle


def _config(path: Path, output_directory: Path | None) -> Path:
    document = {"schema_version": 1}
    if output_directory is not None:
        document["output_directory"] = str(output_directory)
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def test_creator_handle_is_extracted_without_at_query_or_fragment() -> None:
    assert safe_creator_handle(
        "https://www.tiktok.com/@creator_name/live?token=secret#fragment"
    ) == "creator_name"


@pytest.mark.parametrize("url", [
    "https://example.test/@creator/live",
    "https://www.tiktok.com/creator/live",
    "https://www.tiktok.com/@creator/video/123",
    "https://www.tiktok.com/@creator/live/extra",
    "https://token@www.tiktok.com/@creator/live",
    "https://www.tiktok.com:8443/@creator/live",
    "https://www.tiktok.com/@creator%FF/live",
    "https://www.tiktok.com/@creator%ZZ/live",
    "not a URL",
])
def test_nonstandard_url_cannot_supply_automatic_identity(url: str) -> None:
    with pytest.raises(ConfigurationError, match="standard public TikTok"):
        safe_creator_handle(url)


def test_windows_invalid_filename_characters_are_sanitized() -> None:
    assert safe_creator_handle(
        "https://www.tiktok.com/@creator%3Aname%2A%3F/live"
    ) == "creator-name"


def test_automatic_name_and_parts_are_deterministic_direct_children(tmp_path: Path) -> None:
    directory = tmp_path / "recordings"
    config = _config(tmp_path / "config.json", directory)
    output, parts = local_recording_paths(
        "live", "https://www.tiktok.com/@creator/live", None,
        config_path=str(config), clock=lambda: datetime(2026, 9, 21, 18, 45, 0),
    )
    assert output == directory / "creator-20260921-184500.mp4"
    assert parts == directory / "creator-20260921-184500.parts"
    assert output.parent == directory and parts.parent == directory


def test_malicious_handle_text_cannot_escape_configured_directory(tmp_path: Path) -> None:
    directory = tmp_path / "recordings"
    config = _config(tmp_path / "config.json", directory)
    output, parts = local_recording_paths(
        "live", "https://www.tiktok.com/@..%2F..%2Fsecret/live", None,
        config_path=str(config), clock=lambda: datetime(2026, 9, 21, 18, 45, 0),
    )
    assert output.parent == directory and parts.parent == directory
    assert output.name == "secret-20260921-184500.mp4"


def test_output_collision_uses_bounded_deterministic_suffix(tmp_path: Path) -> None:
    directory = tmp_path / "recordings"
    directory.mkdir()
    (directory / "creator-20260921-184500.mp4").write_bytes(b"keep")
    config = _config(tmp_path / "config.json", directory)
    output, parts = local_recording_paths(
        "live", "https://www.tiktok.com/@creator/live", None,
        config_path=str(config), clock=lambda: datetime(2026, 9, 21, 18, 45, 0),
    )
    assert output.name == "creator-20260921-184500-2.mp4"
    assert parts.name == "creator-20260921-184500-2.parts"


def test_parts_collision_also_reserves_matching_output_name(tmp_path: Path) -> None:
    directory = tmp_path / "recordings"
    directory.mkdir()
    (directory / "creator-20260921-184500.parts").mkdir()
    config = _config(tmp_path / "config.json", directory)
    output, parts = local_recording_paths(
        "live", "https://www.tiktok.com/@creator/live", None,
        config_path=str(config), clock=lambda: datetime(2026, 9, 21, 18, 45, 0),
    )
    assert output.name == "creator-20260921-184500-2.mp4"
    assert parts.name == "creator-20260921-184500-2.parts"


def test_collision_search_is_bounded(tmp_path: Path, monkeypatch) -> None:
    import tikrec.output_naming as output_naming

    directory = tmp_path / "recordings"
    directory.mkdir()
    for suffix in ("", "-2"):
        (directory / f"creator-20260921-184500{suffix}.mp4").write_bytes(b"keep")
    config = _config(tmp_path / "config.json", directory)
    monkeypatch.setattr(output_naming, "_MAX_COLLISION_INDEX", 2)
    with pytest.raises(ConfigurationError, match="unused automatic"):
        local_recording_paths(
            "live", "https://www.tiktok.com/@creator/live", None,
            config_path=str(config), clock=lambda: datetime(2026, 9, 21, 18, 45, 0),
        )


def test_missing_configured_directory_fails_actionably(tmp_path: Path) -> None:
    config = _config(tmp_path / "config.json", None)
    with pytest.raises(ConfigurationError, match="config set output-directory"):
        local_recording_paths(
            "live", "https://www.tiktok.com/@creator/live", None,
            config_path=str(config),
        )


def test_explicit_output_keeps_issue_23_precedence(tmp_path: Path) -> None:
    directory = tmp_path / "recordings"
    config = _config(tmp_path / "config.json", directory)
    relative, relative_parts = local_recording_paths(
        "live", "ignored", "chosen.mp4", config_path=str(config)
    )
    absolute = tmp_path / "absolute.mp4"
    explicit, explicit_parts = local_recording_paths(
        "live", "ignored", str(absolute), config_path=str(tmp_path / "bad.json")
    )
    assert relative == directory / "chosen.mp4"
    assert relative_parts == directory / "chosen.parts"
    assert explicit == absolute and explicit_parts == tmp_path / "absolute.parts"
