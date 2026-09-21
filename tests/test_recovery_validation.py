"""Read-only validation decisions for discovered recovery candidates."""

from dataclasses import replace
from pathlib import Path

from tikrec.recovery_discovery import RecoveryCandidate
from tikrec.recovery_validation import validate_recovery_candidates
from tikrec.validation_report import ValidationFinding, ValidationResult


BASE = RecoveryCandidate(
    "/recordings/creator.parts", "a738109c-a387-423f-a20b-969ecf656c4b",
    "tiktok_live", "7687950152400816913", "/recordings/creator.mp4",
    "interrupted", 3, "missing", "incomplete", True, "recoverable", True,
    "Recording ended before finalization — parts appear available for recovery.",
    "Use tikrec finalize with this parts directory and the declared output path.", None,
)


def result(*, passed=True, findings=(), target="/recordings/creator.parts"):
    return ValidationResult(
        target, "session", False, passed, "passed" if passed else "failed",
        "interrupted", "missing", 3, tuple(findings),
    )


def test_recoverable_candidate_validation_passes() -> None:
    calls = []

    def validator(target, *, deep):
        calls.append((target, deep))
        return result()

    validation, = validate_recovery_candidates((BASE,), validator=validator)

    assert calls == [(Path(BASE.parts_directory), False)]
    assert validation.requested and validation.ran and validation.passed
    assert validation.status == "passed"
    assert validation.parts_checked == 3
    assert "appear usable" in validation.summary
    assert "Manual tikrec finalize is available" in validation.next_action


def test_failed_validation_prioritizes_and_limits_findings() -> None:
    findings = tuple(
        [ValidationFinding("warning", "early_warning", "warning", None)]
        + [ValidationFinding("error", f"error_{index}", f"problem {index}", None)
           for index in range(6)]
    )

    validation, = validate_recovery_candidates(
        (BASE,), validator=lambda *_args, **_kwargs: result(passed=False, findings=findings)
    )

    assert validation.status == "failed" and validation.passed is False
    assert validation.finding_count == 7
    assert len(validation.findings) == 5
    assert all(finding.level == "error" for finding in validation.findings)
    assert validation.omitted_findings == 2
    assert "will not recommend finalization" in validation.summary


def test_active_candidate_is_skipped_before_validator_runs() -> None:
    active = replace(
        BASE, lifecycle_state="recording", classification="active_or_uncertain",
        safe_next_action=False,
    )

    def validator(*_args, **_kwargs):
        raise AssertionError("active session must not be validated")

    validation, = validate_recovery_candidates((active,), validator=validator)

    assert validation.status == "skipped"
    assert not validation.ran and validation.passed is None
    assert "may still be active" in validation.summary


def test_ambiguous_candidate_is_skipped_before_validator_runs() -> None:
    ambiguous = replace(
        BASE, evidence_consistent=False, classification="needs_attention",
        safe_next_action=False, untouched_reason="conflicting output",
    )

    def validator(*_args, **_kwargs):
        raise AssertionError("ambiguous session must not be validated")

    validation, = validate_recovery_candidates((ambiguous,), validator=validator)

    assert validation.status == "skipped"
    assert not validation.ran
    assert "incomplete or conflicting" in validation.summary


def test_completed_candidate_validation_does_not_offer_finalization() -> None:
    completed = replace(
        BASE, lifecycle_state="completed", final_output="present",
        finalization_state="complete", classification="complete",
    )

    validation, = validate_recovery_candidates(
        (completed,), validator=lambda *_args, **_kwargs: result()
    )

    assert validation.status == "passed"
    assert "no recovery action is needed" in validation.next_action


def test_validator_exception_fails_closed_without_exception_text() -> None:
    def validator(*_args, **_kwargs):
        raise RuntimeError("signed https://cdn.invalid/secret")

    validation, = validate_recovery_candidates((BASE,), validator=validator)

    assert validation.status == "failed" and validation.ran
    assert validation.findings[0].code == "validation_exception"
    assert "cdn.invalid" not in validation.findings[0].message
    assert "left everything untouched" in validation.summary


def test_changed_target_type_fails_closed() -> None:
    changed = ValidationResult(
        BASE.parts_directory, "parts", False, True, "passed", "unknown",
        "not_declared", 3, (),
    )
    validation, = validate_recovery_candidates(
        (BASE,), validator=lambda *_args, **_kwargs: changed
    )
    assert validation.status == "failed"
    assert validation.findings[0].code == "validation_exception"


def test_validation_wrapper_does_not_mutate_candidate_files(tmp_path: Path) -> None:
    directory = tmp_path / "creator.parts"
    directory.mkdir()
    part = directory / "part-0001.flv"
    manifest = directory / "session.json"
    part.write_bytes(b"retained")
    manifest.write_bytes(b'{"status":"interrupted"}')
    candidate = replace(BASE, parts_directory=str(directory))
    before = {path.name: (path.read_bytes(), path.stat().st_mtime_ns)
              for path in directory.iterdir()}

    def validator(target, *, deep):
        assert target == directory and not deep
        part.read_bytes()
        manifest.read_bytes()
        return result(target=str(target))

    validate_recovery_candidates((candidate,), validator=validator)

    after = {path.name: (path.read_bytes(), path.stat().st_mtime_ns)
             for path in directory.iterdir()}
    assert after == before


def test_validation_json_contains_stable_structured_facts() -> None:
    validation, = validate_recovery_candidates(
        (BASE,), validator=lambda *_args, **_kwargs: result()
    )
    values = validation.as_dict()
    assert values["requested"] is True
    assert values["status"] == "passed"
    assert values["findings"] == []
