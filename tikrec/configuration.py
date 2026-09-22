"""Strict per-user configuration storage and local output-path resolution."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from tempfile import NamedTemporaryFile

from .creator_identity import validate_monitored_creators
from .retry_policy import DEFAULT_RECOVERY_WINDOW_SECONDS


CONFIG_SCHEMA_VERSION = 1
MIN_RECOVERY_WINDOW_SECONDS = 60
MAX_RECOVERY_WINDOW_SECONDS = 3600
DEFAULT_VALIDATION_MODE = "standard"
VALIDATION_MODES = frozenset({"standard", "deep"})
_FIELDS = {
    "schema_version", "output_directory", "recovery_window_seconds", "validation_mode",
    "debug_tracebacks", "monitored_creators",
}


class ConfigurationError(ValueError):
    """The user configuration is malformed, unsupported, or unsafe to use."""


@dataclass(frozen=True)
class Configuration:
    """Supported per-user defaults; secrets are intentionally out of scope."""

    output_directory: Path | None = None
    recovery_window_seconds: int | None = None
    validation_mode: str | None = None
    debug_tracebacks: bool | None = None
    monitored_creators: tuple[str, ...] = ()
    schema_version: int = CONFIG_SCHEMA_VERSION

    def validate(self) -> None:
        """Reject unsupported versions and invalid optional setting values."""
        if type(self.schema_version) is not int or self.schema_version != CONFIG_SCHEMA_VERSION:
            raise ConfigurationError(
                f"unsupported configuration schema version; expected {CONFIG_SCHEMA_VERSION}"
            )
        if self.output_directory is not None:
            _validate_output_directory(self.output_directory)
        if self.recovery_window_seconds is not None:
            validate_recovery_window_seconds(self.recovery_window_seconds)
        if self.validation_mode is not None:
            validate_validation_mode(self.validation_mode)
        if self.debug_tracebacks is not None:
            validate_debug_tracebacks(self.debug_tracebacks)
        validate_monitored_creators(self.monitored_creators)

    @property
    def effective_recovery_window_seconds(self) -> int:
        """Return the configured recovery window or the built-in default."""
        if self.recovery_window_seconds is None:
            return DEFAULT_RECOVERY_WINDOW_SECONDS
        return self.recovery_window_seconds

    @property
    def effective_validation_mode(self) -> str:
        """Return the configured validation mode or the built-in default."""
        return self.validation_mode or DEFAULT_VALIDATION_MODE

    @property
    def effective_debug_tracebacks(self) -> bool:
        """Return the configured traceback preference or the safe built-in default."""
        return self.debug_tracebacks if self.debug_tracebacks is not None else False


def default_config_path(
    *,
    os_name: str | None = None,
    environ: Mapping[str, str] | None = None,
    home: Path | None = None,
) -> Path:
    """Return the deterministic platform configuration path for the current user."""
    platform = os.name if os_name is None else os_name
    variables = os.environ if environ is None else environ
    user_home = Path.home() if home is None else Path(home)
    if platform == "nt":
        base = Path(variables.get("APPDATA") or user_home / "AppData" / "Roaming")
    else:
        configured_base = variables.get("XDG_CONFIG_HOME")
        # The XDG specification requires an absolute value; ignore invalid overrides.
        base = (
            Path(configured_base)
            if configured_base and PurePosixPath(configured_base).is_absolute()
            else user_home / ".config"
        )
    return base / "TikREC" / "config.json"


class ConfigurationStore:
    """Load and atomically replace one strict configuration document."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def load(self) -> Configuration:
        """Return defaults when absent and reject malformed committed configuration."""
        try:
            with self.path.open("r", encoding="utf-8") as handle:
                document = json.load(handle, object_pairs_hook=_unique_fields)
        except FileNotFoundError:
            return Configuration()
        except (OSError, UnicodeError, ValueError) as error:
            raise ConfigurationError(f"invalid configuration at {self.path}: {error}") from None
        try:
            if not isinstance(document, dict) or set(document) - _FIELDS:
                raise ConfigurationError("unknown or invalid top-level fields")
            if "schema_version" not in document:
                raise ConfigurationError("missing schema_version")
            if "validation_mode" in document and document["validation_mode"] is None:
                raise ConfigurationError(
                    "validation_mode must be one of: standard, deep"
                )
            if "debug_tracebacks" in document and document["debug_tracebacks"] is None:
                raise ConfigurationError("debug_tracebacks must be a boolean")
            raw_creators = document.get("monitored_creators", [])
            if type(raw_creators) is not list:
                raise ConfigurationError("monitored_creators must be an ordered list")
            raw_directory = document.get("output_directory")
            if raw_directory is not None and not isinstance(raw_directory, str):
                raise ConfigurationError("output_directory must be an absolute path string")
            configuration = Configuration(
                schema_version=document["schema_version"],
                output_directory=Path(raw_directory) if raw_directory is not None else None,
                recovery_window_seconds=document.get("recovery_window_seconds"),
                validation_mode=document.get("validation_mode"),
                debug_tracebacks=document.get("debug_tracebacks"),
                monitored_creators=tuple(raw_creators),
            )
            configuration.validate()
            return configuration
        except (OSError, TypeError, ValueError) as error:
            detail = str(error) or "invalid document"
            raise ConfigurationError(f"invalid configuration at {self.path}: {detail}") from None

    def save(self, configuration: Configuration) -> None:
        """Flush a complete document before atomically replacing committed configuration."""
        configuration.validate()
        document: dict[str, object] = {"schema_version": configuration.schema_version}
        if configuration.output_directory is not None:
            document["output_directory"] = str(configuration.output_directory)
        if configuration.recovery_window_seconds is not None:
            document["recovery_window_seconds"] = configuration.recovery_window_seconds
        if configuration.validation_mode is not None:
            document["validation_mode"] = configuration.validation_mode
        if configuration.debug_tracebacks is not None:
            document["debug_tracebacks"] = configuration.debug_tracebacks
        if configuration.monitored_creators:
            document["monitored_creators"] = list(configuration.monitored_creators)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary: Path | None = None
        try:
            with NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.path.parent,
                prefix=f".{self.path.name}.",
                suffix=".partial",
                delete=False,
            ) as handle:
                temporary = Path(handle.name)
                json.dump(document, handle, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            # Windows requires the temporary handle to be closed before promotion.
            os.replace(temporary, self.path)
            if os.name != "nt":
                descriptor = os.open(self.path.parent, os.O_RDONLY)
                try:
                    os.fsync(descriptor)
                finally:
                    os.close(descriptor)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)


def configured_output_directory(value: str) -> Path:
    """Normalize a CLI directory to a persistent absolute configuration value."""
    if not isinstance(value, str) or not value.strip() or "\x00" in value or "://" in value:
        raise ConfigurationError("output directory must be a non-empty local path")
    try:
        directory = Path(value).expanduser().resolve(strict=False)
    except (OSError, RuntimeError, ValueError):
        raise ConfigurationError("output directory is not a valid local path") from None
    _validate_output_directory(directory)
    return directory


def validate_recovery_window_seconds(value: object) -> int:
    """Return a strictly bounded integer recovery-window configuration value."""
    if (type(value) is not int
            or not MIN_RECOVERY_WINDOW_SECONDS <= value <= MAX_RECOVERY_WINDOW_SECONDS):
        raise ConfigurationError(
            "recovery_window_seconds must be an integer from "
            f"{MIN_RECOVERY_WINDOW_SECONDS} to {MAX_RECOVERY_WINDOW_SECONDS}"
        )
    return value


def configured_recovery_window_seconds(value: str) -> int:
    """Parse one CLI setting value while preserving strict integer semantics."""
    try:
        parsed: object = int(value)
    except ValueError:
        parsed = value
    return validate_recovery_window_seconds(parsed)


def validate_validation_mode(value: object) -> str:
    """Return a supported validation-mode value with strict type semantics."""
    if type(value) is not str or value not in VALIDATION_MODES:
        raise ConfigurationError("validation_mode must be one of: standard, deep")
    return value


def configured_validation_mode(value: str) -> str:
    """Validate one CLI validation-mode setting value."""
    return validate_validation_mode(value)


def validate_debug_tracebacks(value: object) -> bool:
    """Return a strict boolean traceback preference."""
    if type(value) is not bool:
        raise ConfigurationError("debug_tracebacks must be a boolean")
    return value


def configured_debug_tracebacks(value: str) -> bool:
    """Parse the lowercase boolean accepted by the configuration CLI."""
    if value not in {"true", "false"}:
        raise ConfigurationError("debug tracebacks must be true or false")
    return value == "true"


def resolve_recording_output(output: str | Path, configuration: Configuration) -> Path:
    """Apply the configured base only to relative local recording output paths."""
    path = Path(output)
    if path.is_absolute() or configuration.output_directory is None:
        return path
    base = configuration.output_directory.resolve(strict=False)
    candidate = (base / path).resolve(strict=False)
    try:
        candidate.relative_to(base)
    except ValueError:
        raise ConfigurationError(
            "relative --output must stay beneath configured output_directory"
        ) from None
    return candidate


def _validate_output_directory(directory: Path) -> None:
    value = str(directory)
    if not value.strip() or "\x00" in value or "://" in value or not directory.is_absolute():
        raise ConfigurationError("output_directory must be a non-empty absolute local path")
    if directory.exists() and not directory.is_dir():
        raise ConfigurationError("output_directory exists but is not a directory")


def _unique_fields(pairs: list[tuple[str, object]]) -> dict[str, object]:
    values: dict[str, object] = {}
    for name, value in pairs:
        if name in values:
            raise ValueError(f"duplicate field: {name}")
        values[name] = value
    return values
