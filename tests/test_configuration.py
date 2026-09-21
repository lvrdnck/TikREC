"""Strict configuration storage, discovery, and path-resolution tests."""

import json
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import pytest

from tikrec.configuration import (
    CONFIG_SCHEMA_VERSION,
    Configuration,
    ConfigurationError,
    ConfigurationStore,
    configured_output_directory,
    default_config_path,
    resolve_recording_output,
)


def test_default_config_path_uses_windows_roaming_convention() -> None:
    path = default_config_path(
        os_name="nt",
        environ={"APPDATA": r"C:\Users\person\AppData\Roaming"},
        home=Path(r"C:\Users\ignored"),
    )
    assert str(path) == r"C:\Users\person\AppData\Roaming\TikREC\config.json"


def test_default_config_path_uses_xdg_and_posix_fallback() -> None:
    assert default_config_path(
        os_name="posix", environ={"XDG_CONFIG_HOME": "/config"}, home=Path("/home/person")
    ) == Path("/config/TikREC/config.json")
    assert default_config_path(
        os_name="posix", environ={}, home=Path("/home/person")
    ) == Path("/home/person/.config/TikREC/config.json")
    assert default_config_path(
        os_name="posix", environ={"XDG_CONFIG_HOME": "relative"}, home=Path("/home/person")
    ) == Path("/home/person/.config/TikREC/config.json")


def test_missing_configuration_preserves_relative_output(tmp_path: Path) -> None:
    configuration = ConfigurationStore(tmp_path / "missing.json").load()
    assert configuration == Configuration()
    assert resolve_recording_output("recording.mp4", configuration) == Path("recording.mp4")


def test_valid_configuration_loads_and_resolves_beneath_directory(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    output_directory = tmp_path / "recordings"
    path.write_text(json.dumps({
        "schema_version": CONFIG_SCHEMA_VERSION,
        "output_directory": str(output_directory),
    }), encoding="utf-8")
    configuration = ConfigurationStore(path).load()
    assert configuration.output_directory == output_directory
    assert resolve_recording_output("creator/live.mp4", configuration) == (
        output_directory / "creator/live.mp4"
    )


@pytest.mark.parametrize("content, message", [
    ("{", "invalid configuration"),
    ('{"schema_version": 2}', "unsupported configuration schema version"),
    ('{"schema_version": 1, "output_directory": 7}', "absolute path string"),
    ('{"schema_version": 1, "typo": true}', "unknown or invalid"),
    ('{"schema_version": 1, "schema_version": 1}', "duplicate field"),
    ('{"output_directory": "/recordings"}', "missing schema_version"),
])
def test_invalid_configuration_fails_clearly(
    tmp_path: Path, content: str, message: str
) -> None:
    path = tmp_path / "config.json"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(ConfigurationError, match=message):
        ConfigurationStore(path).load()


def test_configured_directory_must_be_absolute_and_not_a_file(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError, match="absolute"):
        Configuration(output_directory=Path("relative")).validate()
    file_path = tmp_path / "file"
    file_path.write_text("occupied", encoding="utf-8")
    with pytest.raises(ConfigurationError, match="not a directory"):
        configured_output_directory(str(file_path))


def test_relative_cli_value_is_stored_as_absolute_without_creating_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    directory = configured_output_directory("future/recordings")
    assert directory == tmp_path / "future/recordings"
    assert not directory.exists()


def test_absolute_output_ignores_configured_directory(tmp_path: Path) -> None:
    configuration = Configuration(output_directory=tmp_path / "configured")
    absolute = tmp_path / "explicit.mp4"
    assert resolve_recording_output(absolute, configuration) == absolute


def test_relative_output_cannot_escape_configured_directory(tmp_path: Path) -> None:
    configuration = Configuration(output_directory=tmp_path / "configured")
    with pytest.raises(ConfigurationError, match="stay beneath"):
        resolve_recording_output("../outside.mp4", configuration)


def test_atomic_save_replaces_complete_document_and_leaves_no_partial(tmp_path: Path) -> None:
    path = tmp_path / "config" / "config.json"
    store = ConfigurationStore(path)
    directory = tmp_path / "recordings"
    store.save(Configuration(output_directory=directory))
    assert store.load().output_directory == directory
    assert list(path.parent.glob("*.partial")) == []
    assert json.loads(path.read_text(encoding="utf-8")) == {
        "output_directory": str(directory), "schema_version": 1,
    }


def test_failed_atomic_replace_preserves_previous_configuration(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    store = ConfigurationStore(path)
    original = Configuration(output_directory=tmp_path / "original")
    store.save(original)
    with patch("tikrec.configuration.os.replace", side_effect=OSError("disk failure")):
        with pytest.raises(OSError, match="disk failure"):
            store.save(replace(original, output_directory=tmp_path / "new"))
    assert store.load() == original
    assert list(tmp_path.glob("*.partial")) == []
