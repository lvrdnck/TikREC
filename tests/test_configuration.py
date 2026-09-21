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
    configured_debug_tracebacks,
    configured_recovery_window_seconds,
    configured_output_directory,
    configured_validation_mode,
    default_config_path,
    resolve_recording_output,
    validate_recovery_window_seconds,
    validate_debug_tracebacks,
    validate_validation_mode,
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
        "recovery_window_seconds": 600,
        "validation_mode": "deep",
        "debug_tracebacks": False,
    }), encoding="utf-8")
    configuration = ConfigurationStore(path).load()
    assert configuration.output_directory == output_directory
    assert configuration.recovery_window_seconds == 600
    assert configuration.effective_recovery_window_seconds == 600
    assert configuration.validation_mode == "deep"
    assert configuration.effective_validation_mode == "deep"
    assert configuration.debug_tracebacks is False
    assert configuration.effective_debug_tracebacks is False
    assert resolve_recording_output("creator/live.mp4", configuration) == (
        output_directory / "creator/live.mp4"
    )


@pytest.mark.parametrize("content, message", [
    ("{", "invalid configuration"),
    ('{"schema_version": 2}', "unsupported configuration schema version"),
    ('{"schema_version": 1, "output_directory": 7}', "absolute path string"),
    ('{"schema_version": 1, "recovery_window_seconds": true}', "integer from 60 to 3600"),
    ('{"schema_version": 1, "recovery_window_seconds": 60.0}', "integer from 60 to 3600"),
    ('{"schema_version": 1, "recovery_window_seconds": "60"}', "integer from 60 to 3600"),
    ('{"schema_version": 1, "recovery_window_seconds": 59}', "integer from 60 to 3600"),
    ('{"schema_version": 1, "recovery_window_seconds": 3601}', "integer from 60 to 3600"),
    ('{"schema_version": 1, "validation_mode": "fast"}', "one of: standard, deep"),
    ('{"schema_version": 1, "validation_mode": true}', "one of: standard, deep"),
    ('{"schema_version": 1, "validation_mode": 1}', "one of: standard, deep"),
    ('{"schema_version": 1, "validation_mode": null}', "one of: standard, deep"),
    ('{"schema_version": 1, "debug_tracebacks": 1}', "must be a boolean"),
    ('{"schema_version": 1, "debug_tracebacks": "false"}', "must be a boolean"),
    ('{"schema_version": 1, "debug_tracebacks": null}', "must be a boolean"),
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


def test_recovery_window_bounds_and_default_are_strict() -> None:
    assert Configuration().effective_recovery_window_seconds == 900
    assert validate_recovery_window_seconds(60) == 60
    assert validate_recovery_window_seconds(3600) == 3600
    for invalid in (True, 59, 3601, 60.0, "60", 0, -1):
        with pytest.raises(ConfigurationError, match="integer from 60 to 3600"):
            validate_recovery_window_seconds(invalid)
    assert configured_recovery_window_seconds("600") == 600


def test_validation_mode_values_and_default_are_strict() -> None:
    assert Configuration().effective_validation_mode == "standard"
    assert validate_validation_mode("standard") == "standard"
    assert configured_validation_mode("deep") == "deep"
    for invalid in ("fast", True, 1, None, 1.0):
        with pytest.raises(ConfigurationError, match="one of: standard, deep"):
            validate_validation_mode(invalid)


def test_debug_traceback_values_and_default_are_strict() -> None:
    assert Configuration().effective_debug_tracebacks is False
    assert validate_debug_tracebacks(True) is True
    assert configured_debug_tracebacks("false") is False
    for invalid in (1, 0, None, "false", 1.0):
        with pytest.raises(ConfigurationError, match="must be a boolean"):
            validate_debug_tracebacks(invalid)
    for invalid in ("False", "yes", "1", ""):
        with pytest.raises(ConfigurationError, match="true or false"):
            configured_debug_tracebacks(invalid)


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
    store.save(Configuration(
        output_directory=directory, recovery_window_seconds=1200, validation_mode="standard",
        debug_tracebacks=False,
    ))
    assert store.load() == Configuration(
        output_directory=directory, recovery_window_seconds=1200, validation_mode="standard",
        debug_tracebacks=False,
    )
    assert list(path.parent.glob("*.partial")) == []
    assert json.loads(path.read_text(encoding="utf-8")) == {
        "output_directory": str(directory), "recovery_window_seconds": 1200,
        "schema_version": 1, "validation_mode": "standard", "debug_tracebacks": False,
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
