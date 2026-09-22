"""Selective, strict service-start configuration tests."""

import json
from pathlib import Path

import pytest

from tikrec.configuration import ConfigurationError
from tikrec.service_configuration import (
    ServiceConfiguration,
    load_service_configuration,
)


def test_absent_service_configuration_uses_safe_defaults(tmp_path: Path):
    assert load_service_configuration(
        tmp_path / "missing.json", validate_all=True
    ) == ServiceConfiguration()
    assert load_service_configuration(
        tmp_path / "missing.json", validate_all=False
    ) == ServiceConfiguration()


def test_full_service_configuration_snapshots_all_needed_settings(tmp_path: Path):
    path = tmp_path / "config.json"
    directory = tmp_path / "recordings"
    path.write_text(json.dumps({
        "schema_version": 1,
        "output_directory": str(directory),
        "recovery_window_seconds": 600,
        "validation_mode": "deep",
        "debug_tracebacks": True,
        "monitored_creators": ["first", "second.creator"],
    }), encoding="utf-8")
    assert load_service_configuration(path, validate_all=True) == ServiceConfiguration(
        output_directory=directory,
        monitored_creators=("first", "second.creator"),
        recovery_window_seconds=600,
    )


def test_explicit_recovery_override_ignores_only_unneeded_preferences(tmp_path: Path):
    path = tmp_path / "config.json"
    directory = tmp_path / "recordings"
    path.write_text(json.dumps({
        "schema_version": 1,
        "output_directory": str(directory),
        "recovery_window_seconds": "invalid-but-overridden",
        "validation_mode": "invalid-but-unused",
        "debug_tracebacks": "invalid-but-unused",
        "monitored_creators": ["first", "second.creator"],
    }), encoding="utf-8")
    assert load_service_configuration(path, validate_all=False) == ServiceConfiguration(
        output_directory=directory,
        monitored_creators=("first", "second.creator"),
    )
    with pytest.raises(ConfigurationError):
        load_service_configuration(path, validate_all=True)


@pytest.mark.parametrize("document", [
    {"monitored_creators": ["first"]},
    {"schema_version": True},
    {"schema_version": 2},
    {"schema_version": 1, "output_directory": 7},
    {"schema_version": 1, "monitored_creators": ["First"]},
    {"schema_version": 1, "monitored_creators": ["first", "first"]},
    {"schema_version": 1, "monitored_creators": "first"},
    {"schema_version": 1, "unknown": True},
])
def test_selective_loader_keeps_schema_and_needed_fields_strict(
    tmp_path: Path, document: dict
):
    path = tmp_path / "config.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ConfigurationError):
        load_service_configuration(path, validate_all=False)


@pytest.mark.parametrize("content", [
    "{",
    '{"schema_version": 1, "schema_version": 1}',
])
def test_selective_loader_rejects_malformed_or_duplicate_json(
    tmp_path: Path, content: str
):
    path = tmp_path / "config.json"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(ConfigurationError):
        load_service_configuration(path, validate_all=False)


def test_selective_loader_rejects_output_path_that_is_an_existing_file(
    tmp_path: Path,
):
    occupied = tmp_path / "occupied"
    occupied.write_text("not a directory", encoding="utf-8")
    path = tmp_path / "config.json"
    path.write_text(json.dumps({
        "schema_version": 1,
        "output_directory": str(occupied),
    }), encoding="utf-8")
    with pytest.raises(ConfigurationError, match="not a directory"):
        load_service_configuration(path, validate_all=False)
