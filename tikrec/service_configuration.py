"""Select only configuration fields needed by the persistent service."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .configuration import (CONFIG_SCHEMA_VERSION, Configuration,
                            ConfigurationError, ConfigurationStore)
from .retry_policy import DEFAULT_RECOVERY_WINDOW_SECONDS
from .storage_status import DEFAULT_MINIMUM_FREE_SPACE_GIB


_FIELDS = {
    "schema_version", "output_directory", "recovery_window_seconds",
    "validation_mode", "debug_tracebacks", "monitored_creators", "minimum_free_space_gib",
    "retention_protected_creators", "retention_max_age_days",
}


@dataclass(frozen=True)
class ServiceConfiguration:
    """Immutable startup storage and creator settings used by the service."""

    output_directory: Path | None = None
    monitored_creators: tuple[str, ...] = ()
    recovery_window_seconds: int = DEFAULT_RECOVERY_WINDOW_SECONDS
    minimum_free_space_gib: int = DEFAULT_MINIMUM_FREE_SPACE_GIB


def load_service_configuration(
    path: Path, *, validate_all: bool
) -> ServiceConfiguration:
    """Load a full document or only service fields for an explicit CLI override."""
    store = ConfigurationStore(path)
    if validate_all:
        configuration = store.load()
        return ServiceConfiguration(
            output_directory=configuration.output_directory,
            monitored_creators=configuration.monitored_creators,
            recovery_window_seconds=configuration.effective_recovery_window_seconds,
            minimum_free_space_gib=configuration.effective_minimum_free_space_gib,
        )
    try:
        with path.open("r", encoding="utf-8") as handle:
            document = json.load(handle, object_pairs_hook=_unique_fields)
    except FileNotFoundError:
        return ServiceConfiguration()
    except (OSError, UnicodeError, ValueError) as error:
        raise ConfigurationError(f"invalid configuration at {path}: {error}") from None
    try:
        if not isinstance(document, dict) or set(document) - _FIELDS:
            raise ConfigurationError("unknown or invalid top-level fields")
        if "schema_version" not in document:
            raise ConfigurationError("missing schema_version")
        version = document["schema_version"]
        if type(version) is not int or version != CONFIG_SCHEMA_VERSION:
            raise ConfigurationError(
                f"unsupported configuration schema version; expected {CONFIG_SCHEMA_VERSION}"
            )
        raw_directory = document.get("output_directory")
        if raw_directory is not None and not isinstance(raw_directory, str):
            raise ConfigurationError("output_directory must be an absolute path string")
        raw_creators = document.get("monitored_creators", [])
        if type(raw_creators) is not list:
            raise ConfigurationError("monitored_creators must be an ordered list")
        selected = Configuration(
            schema_version=version,
            output_directory=Path(raw_directory) if raw_directory is not None else None,
            monitored_creators=tuple(raw_creators),
            minimum_free_space_gib=document.get("minimum_free_space_gib"),
        )
        if "minimum_free_space_gib" in document and document["minimum_free_space_gib"] is None:
            raise ConfigurationError("minimum_free_space_gib must be an integer")
        selected.validate()
        return ServiceConfiguration(
            output_directory=selected.output_directory,
            monitored_creators=selected.monitored_creators,
            minimum_free_space_gib=selected.effective_minimum_free_space_gib,
        )
    except (OSError, TypeError, ValueError) as error:
        detail = str(error) or "invalid document"
        raise ConfigurationError(f"invalid configuration at {path}: {detail}") from None


def _unique_fields(pairs: list[tuple[str, object]]) -> dict[str, object]:
    values: dict[str, object] = {}
    for name, value in pairs:
        if name in values:
            raise ValueError(f"duplicate field: {name}")
        values[name] = value
    return values
