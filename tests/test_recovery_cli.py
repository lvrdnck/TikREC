"""User-facing and structured output for read-only recovery discovery."""

import json
from dataclasses import replace
from io import StringIO
from pathlib import Path

from tikrec.cli import main
from tikrec.recovery_cli import render_recovery_report
from tikrec.recovery_discovery import RecoveryCandidate
from tikrec.validation_report import ValidationFinding, ValidationResult


BASE = RecoveryCandidate(
    parts_directory="/recordings/creator.parts",
    session_id="a738109c-a387-423f-a20b-969ecf656c4b",
    source_type="tiktok_live",
    room_id="7687950152400816913",
    output_path="/recordings/creator.mp4",
    lifecycle_state="interrupted",
    retained_parts=3,
    final_output="missing",
    finalization_state="incomplete",
    evidence_consistent=True,
    classification="recoverable",
    safe_next_action=True,
    summary="Recording ended before finalization — parts appear available for recovery.",
    next_action="Use tikrec finalize with this parts directory and the declared output path.",
    untouched_reason=None,
)


def test_recover_prints_plain_language_session_facts() -> None:
    stdout = StringIO()

    code = main(
        ["recover", "/recordings"],
        recovery_discoverer=lambda _: (BASE,), stdout=stdout,
    )

    assert code == 0
    report = stdout.getvalue()
    assert f"Recovery candidates in {Path('/recordings')}: 1" in report
    assert "Session: a738109c-a387-423f-a20b-969ecf656c4b" in report
    assert "Source: TikTok LIVE (room 7687950152400816913)" in report
    assert "Retained parts: 3" in report
    assert "parts appear available for recovery" in report


def test_recover_json_is_machine_readable() -> None:
    stdout = StringIO()

    code = main(
        ["recover", "recordings", "--json"],
        recovery_discoverer=lambda _: (BASE,), stdout=stdout,
    )

    document = json.loads(stdout.getvalue())
    assert code == 0
    assert document["scope"] == "recordings"
    assert document["candidate_count"] == 1
    assert document["candidates"][0]["classification"] == "recoverable"
    assert "validation_requested" not in document
    assert "validation" not in document["candidates"][0]


def test_recover_validate_prints_guided_result() -> None:
    stdout = StringIO()
    validation = ValidationResult(
        BASE.parts_directory, "session", False, True, "passed", "interrupted",
        "missing", 3, (ValidationFinding("warning", "output_missing", "missing", None),),
    )

    code = main(
        ["recover", "recordings", "--validate"],
        recovery_discoverer=lambda _: (BASE,), validator=lambda *_args, **_kwargs: validation,
        stdout=stdout,
    )

    report = stdout.getvalue()
    assert code == 0
    assert "Validation requested: yes" in report
    assert "Validation ran: yes" in report
    assert "Validation result: passed" in report
    assert "retained recording parts appear usable" in report
    assert "Manual tikrec finalize is available" in report


def test_recovery_validation_ignores_configured_deep_mode(tmp_path: Path) -> None:
    config = tmp_path / "config.json"
    config.write_text(json.dumps({
        "schema_version": 1, "validation_mode": "deep",
    }), encoding="utf-8")
    modes = []

    def validator(target, *, deep):
        modes.append(deep)
        return ValidationResult(
            str(target), "session", deep, True, "passed", "interrupted", "missing", 3, (),
        )

    assert main([
        "--config", str(config), "recover", "recordings", "--validate",
    ], recovery_discoverer=lambda _: (BASE,), validator=validator,
       stdout=StringIO()) == 0
    assert modes == [False]


def test_recover_validate_json_includes_structured_validation() -> None:
    stdout = StringIO()
    validation = ValidationResult(
        BASE.parts_directory, "session", False, False, "failed", "interrupted",
        "missing", 3, (ValidationFinding("error", "part_decode", "damaged", None),),
    )

    code = main(
        ["recover", "recordings", "--validate", "--json"],
        recovery_discoverer=lambda _: (BASE,), validator=lambda *_args, **_kwargs: validation,
        stdout=stdout,
    )

    document = json.loads(stdout.getvalue())
    guided = document["candidates"][0]["validation"]
    assert code == 1
    assert document["validation_requested"] is True
    assert guided["status"] == "failed"
    assert guided["ran"] is True
    assert guided["findings"][0]["code"] == "part_decode"


def test_recover_without_validate_never_calls_validator() -> None:
    def validator(*_args, **_kwargs):
        raise AssertionError("validation was not requested")

    code = main(
        ["recover", "recordings"], recovery_discoverer=lambda _: (BASE,),
        validator=validator, stdout=StringIO(),
    )
    assert code == 0


def test_recover_validate_skips_active_candidate_and_exits_nonzero() -> None:
    active = replace(
        BASE, lifecycle_state="recording", classification="active_or_uncertain",
        safe_next_action=False,
    )

    def validator(*_args, **_kwargs):
        raise AssertionError("active candidate must be skipped")

    stdout = StringIO()
    code = main(
        ["recover", "recordings", "--validate"],
        recovery_discoverer=lambda _: (active,), validator=validator, stdout=stdout,
    )
    assert code == 1
    assert "Validation ran: no" in stdout.getvalue()
    assert "This session may still be active — validation was skipped." in stdout.getvalue()


def test_recover_reports_empty_scope_plainly() -> None:
    stdout = StringIO()
    code = main(
        ["recover", "empty"], recovery_discoverer=lambda _: (), stdout=stdout
    )
    assert code == 0
    assert stdout.getvalue() == "No TikREC recovery candidates found in empty.\n"


def test_recover_validate_reports_empty_scope_without_failure() -> None:
    stdout = StringIO()
    code = main(
        ["recover", "empty", "--validate"],
        recovery_discoverer=lambda _: (), stdout=stdout,
    )
    assert code == 0
    assert "Validation was requested; nothing was validated." in stdout.getvalue()


def test_recover_errors_use_existing_cli_error_contract() -> None:
    def fail(_: Path):
        raise ValueError("recovery scope must be a regular directory")

    stderr = StringIO()
    code = main(["recover", "missing"], recovery_discoverer=fail, stderr=stderr)
    assert code == 1
    assert stderr.getvalue() == "tikrec: recovery scope must be a regular directory\n"


def test_render_preserves_windows_and_posix_paths() -> None:
    windows = replace(
        BASE,
        parts_directory=r"C:\Videos\creator.parts",
        output_path=r"C:\Videos\creator.mp4",
    )
    report = render_recovery_report(Path("."), (windows, BASE))
    assert r"C:\Videos\creator.parts" in report
    assert r"C:\Videos\creator.mp4" in report
    assert "/recordings/creator.parts" in report
