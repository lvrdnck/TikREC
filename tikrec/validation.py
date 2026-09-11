"""Read-only validation of TikREC outputs, parts, and session manifests."""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .manifest import SCHEMA_VERSION
from .media import MediaInfo, inspect_media
from .part_validation import validate_part
from .validation_report import ValidationFinding, ValidationResult, render_validation


class _ResultBuilder:
    def __init__(self, target: Path, target_type: str) -> None:
        self.target = target
        self.target_type = target_type
        self.media_integrity = "not_checked"
        self.session_completeness = "not_applicable"
        self.output_availability = "not_applicable"
        self.parts_checked = 0
        self.findings: list[ValidationFinding] = []

    def finding(self, level: str, code: str, message: str, path: Path | None = None) -> None:
        self.findings.append(
            ValidationFinding(level, code, message, None if path is None else str(path))
        )

    def finish(self) -> ValidationResult:
        passed = not any(finding.level == "error" for finding in self.findings)
        return ValidationResult(
            str(self.target), self.target_type, passed, self.media_integrity,
            self.session_completeness, self.output_availability,
            self.parts_checked, tuple(self.findings),
        )


def validate_target(
    target: Path,
    *,
    ffprobe: str = "ffprobe",
    runner: Callable[..., Any] = subprocess.run,
) -> ValidationResult:
    """Validate a completed output, parts directory, or v0.2 session."""
    target = Path(target)
    if not target.exists():
        result = _ResultBuilder(target, "missing")
        result.output_availability = "missing"
        result.finding("error", "target_missing", "target does not exist", target)
        return result.finish()
    if target.is_file():
        if target.name == "session.json":
            return _validate_session(target.parent, ffprobe, runner)
        return _validate_output_target(target, ffprobe, runner)
    if target.is_dir():
        if (target / "session.json").exists():
            return _validate_session(target, ffprobe, runner)
        return _validate_parts_target(target, ffprobe, runner)
    result = _ResultBuilder(target, "unsupported")
    result.finding("error", "target_unsupported", "target is not a regular file or directory")
    return result.finish()

def _validate_parts_target(
    directory: Path, ffprobe: str, runner: Callable[..., Any]
) -> ValidationResult:
    result = _ResultBuilder(directory, "parts")
    result.session_completeness = "unknown"
    result.output_availability = "not_declared"
    result.finding(
        "warning", "manifest_missing",
        "legacy parts directory has no session.json; session consistency was not checked",
    )
    _validate_parts(directory, result, ffprobe, runner)
    return result.finish()

def _validate_output_target(
    output: Path, ffprobe: str, runner: Callable[..., Any]
) -> ValidationResult:
    result = _ResultBuilder(output, "output")
    result.output_availability = "present"
    _validate_output(output, result, ffprobe, runner)
    return result.finish()

def _validate_session(
    directory: Path, ffprobe: str, runner: Callable[..., Any]
) -> ValidationResult:
    result = _ResultBuilder(directory, "session")
    manifest = _read_manifest(directory / "session.json", result)
    _validate_parts(directory, result, ffprobe, runner)
    if manifest is None:
        return result.finish()
    _validate_manifest(directory, manifest, result, ffprobe, runner)
    return result.finish()

def _validate_parts(
    directory: Path,
    result: _ResultBuilder,
    ffprobe: str,
    runner: Callable[..., Any],
) -> None:
    parts = tuple(sorted(directory.glob("part-*.flv")))
    if not parts:
        result.media_integrity = "failed"
        result.finding("error", "parts_missing", "no retained FLV parts were found", directory)
        return
    media_failed = False
    for part in parts:
        result.parts_checked += 1
        if not _readable_nonempty(part, result, "part"):
            media_failed = True
            continue
        try:
            problems, warnings = validate_part(part, ffprobe, runner)
        except OSError as error:
            result.finding("error", "ffprobe_unavailable", f"could not start FFprobe: {error}")
            media_failed = True
            continue
        for check, message in problems:
            result.finding("error", f"part_{check.lower()}", message, part)
            media_failed = True
        for check, message in warnings:
            result.finding("warning", f"part_{check.lower()}_warning", message, part)
        info = inspect_media(part, ffprobe=ffprobe, runner=runner)
        if info is None or info.video_codec is None:
            result.finding("error", "part_video_missing", "no recognizable video stream", part)
            media_failed = True
        elif info.audio_codec is None:
            result.finding("warning", "part_audio_missing", "no recognizable audio stream", part)
    result.media_integrity = "failed" if media_failed else "passed"

def _read_manifest(path: Path, result: _ResultBuilder) -> dict[str, Any] | None:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        result.session_completeness = "unknown"
        result.finding("error", "manifest_unreadable", f"could not read session.json: {error}", path)
        return None
    if not isinstance(document, dict):
        result.finding("error", "manifest_malformed", "session.json root is not an object", path)
        return None
    if document.get("schema_version") != SCHEMA_VERSION:
        result.finding(
            "error", "manifest_schema_unsupported",
            f"unsupported session manifest schema: {document.get('schema_version')!r}", path,
        )
        return None
    return document

def _validate_manifest(
    directory: Path,
    manifest: dict[str, Any],
    result: _ResultBuilder,
    ffprobe: str,
    runner: Callable[..., Any],
) -> None:
    status = manifest.get("status")
    result.session_completeness = _session_state(status)
    if status not in {"recording", "completed", "interrupted", "failed"}:
        result.finding("error", "manifest_status_invalid", "manifest status is invalid")
    expected_count = manifest.get("part_count")
    if not isinstance(expected_count, int) or isinstance(expected_count, bool) or expected_count < 0:
        result.finding("error", "manifest_part_count_invalid", "manifest part_count is invalid")
    elif expected_count != result.parts_checked:
        result.finding(
            "error", "manifest_part_count_mismatch",
            f"manifest declares {expected_count} parts but {result.parts_checked} were found",
        )
    finalization = manifest.get("finalization")
    if not isinstance(finalization, dict) or not isinstance(finalization.get("status"), str):
        result.finding("error", "manifest_finalization_invalid", "manifest finalization is invalid")
        finalization_status = None
    else:
        finalization_status = finalization["status"]
        allowed_finalization = {
            "not_requested", "pending", "not_started", "running",
            "completed", "interrupted", "failed",
        }
        if finalization_status not in allowed_finalization:
            result.finding(
                "error", "manifest_finalization_invalid", "manifest finalization status is invalid"
            )
    if status == "completed" and finalization_status not in {"completed", "not_requested"}:
        result.finding(
            "error", "manifest_state_inconsistent",
            f"completed session has finalization status {finalization_status!r}",
        )
    if status == "recording" and finalization_status == "completed":
        result.finding(
            "error", "manifest_state_inconsistent",
            "recording session claims completed finalization",
        )
    output = _manifest_output(directory, manifest, result)
    if output is None:
        result.output_availability = "not_declared"
        if finalization_status == "completed":
            result.finding(
                "error", "completed_output_undeclared",
                "finalization is completed but no output path is declared",
            )
        return
    result.output_availability = "present" if output.is_file() else "missing"
    if not output.is_file():
        level = "error" if finalization_status == "completed" else "warning"
        result.finding(level, "output_missing", "declared output does not exist", output)
        return
    output_info = _validate_output(output, result, ffprobe, runner)
    if finalization_status != "completed":
        result.finding(
            "warning", "output_state_unexpected",
            f"output exists while finalization status is {finalization_status!r}", output,
        )
    if output_info is not None:
        _compare_media(manifest.get("media"), output_info, result, output)

def _manifest_output(
    directory: Path, manifest: dict[str, Any], result: _ResultBuilder
) -> Path | None:
    value = manifest.get("output_path")
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        result.finding("error", "manifest_output_invalid", "manifest output_path is invalid")
        return None
    output = Path(value)
    if output.is_absolute() or output.exists():
        return output
    declared_parts = manifest.get("parts_directory")
    if isinstance(declared_parts, str):
        suffix = Path(declared_parts).parts
        actual = directory.parts
        if suffix and len(actual) >= len(suffix) and actual[-len(suffix):] == suffix:
            # Recover the original relative-path base from the relocated session target.
            return Path(*actual[:-len(suffix)]) / output
    return output

def _validate_output(
    output: Path, result: _ResultBuilder, ffprobe: str, runner: Callable[..., Any]
) -> MediaInfo | None:
    if not _readable_nonempty(output, result, "output"):
        result.media_integrity = "failed"
        return None
    info = inspect_media(output, ffprobe=ffprobe, runner=runner)
    if info is None:
        result.finding("error", "output_probe_failed", "FFprobe could not inspect the output", output)
        result.media_integrity = "failed"
        return None
    failed = False
    for code, value, message in (
        ("output_video_missing", info.video_codec, "no recognizable video stream"),
        ("output_format_missing", info.format_name, "container format was not recognized"),
        ("output_duration_invalid", info.duration_seconds, "duration is missing or not positive"),
    ):
        if value is None:
            result.finding("error", code, message, output)
            failed = True
    if info.audio_codec is None:
        result.finding("warning", "output_audio_missing", "no recognizable audio stream", output)
    if result.media_integrity != "failed":
        result.media_integrity = "failed" if failed else "passed"
    return info

def _readable_nonempty(path: Path, result: _ResultBuilder, prefix: str) -> bool:
    try:
        if not path.is_file() or path.stat().st_size == 0:
            reason = "is not a non-empty regular file"
            raise ValueError(reason)
        with path.open("rb") as handle:
            handle.read(1)
    except (OSError, ValueError) as error:
        result.finding("error", f"{prefix}_unreadable", str(error), path)
        return False
    return True

def _compare_media(
    declared: Any, actual: MediaInfo, result: _ResultBuilder, output: Path
) -> None:
    if declared is None:
        return
    if not isinstance(declared, dict):
        result.finding("error", "manifest_media_invalid", "manifest media is not an object")
        return
    for key in ("video_codec", "audio_codec", "width", "height"):
        expected = declared.get(key)
        if expected is not None and expected != getattr(actual, key):
            result.finding(
                "error", "manifest_media_mismatch",
                f"manifest {key} is {expected!r}, FFprobe reports {getattr(actual, key)!r}",
                output,
            )

def _session_state(status: Any) -> str:
    if status == "completed":
        return "complete"
    if status in {"recording", "interrupted", "failed"}:
        return str(status)
    return "unknown"
