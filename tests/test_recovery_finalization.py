"""Offline checks for explicit, single-session guided finalization."""

from __future__ import annotations

import json
from io import StringIO
from pathlib import Path

from tests.test_session_parts import populate
from tikrec.cli import main
from tikrec.manifest import SessionManifest
from tikrec.media import MediaInfo
from tikrec.recovery_discovery import discover_recovery_candidates
from tikrec.recovery_finalization import guided_finalize
from tikrec.validation_report import ValidationFinding, ValidationResult


IDENTITY = "a738109c-a387-423f-a20b-969ecf656c4b"
MEDIA = MediaInfo("h264", "aac", 720, 1280, "mov,mp4", 12.5)


def make_session(
    root: Path,
    *,
    status: str = "interrupted",
    finalization: str = "interrupted",
    output_declared: bool = True,
) -> tuple[Path, Path | None]:
    directory = root / "creator.parts"
    directory.mkdir()
    populate(directory, 1)
    output = root / "creator.mp4" if output_declared else None
    manifest = SessionManifest(
        directory, output, "tiktok_live", session_id=IDENTITY,
        clock=iter((1000.0, 1010.0)).__next__, media_inspector=lambda _: MEDIA,
    )
    manifest.start(connection_count=1)
    manifest.record_room_identity("7687950152400816913")
    parts = tuple(directory.glob("part-*.flv"))
    if status == "recording":
        manifest.update_capture(parts)
    else:
        manifest.finish(
            status, parts, interrupted=status == "interrupted",
            finalization_status=finalization,
            error="capture failed" if status == "failed" else None,
        )
    return directory, output


def discover(scope: Path):
    return discover_recovery_candidates(scope, media_inspector=lambda _: MEDIA)


def validation(
    directory: Path,
    *,
    passed: bool = True,
    output: str = "missing",
) -> ValidationResult:
    findings = () if passed else (
        ValidationFinding("error", "part_decode", "retained part did not decode"),
    )
    return ValidationResult(
        str(directory), "session", False, passed,
        "passed" if passed else "failed", "interrupted", output, 1, findings,
    )


class Validator:
    def __init__(self, directory: Path, *, pre_passes=True, post_passes=True) -> None:
        self.directory = directory
        self.pre_passes = pre_passes
        self.post_passes = post_passes
        self.calls = 0

    def __call__(self, target: Path, *, deep: bool) -> ValidationResult:
        assert Path(target) == self.directory
        assert deep is False
        self.calls += 1
        if self.calls == 1:
            return validation(target, passed=self.pre_passes)
        return validation(target, passed=self.post_passes, output="present")


def finalize(directory, *, validator, finalizer):
    candidates = discover(directory)
    return guided_finalize(
        directory, candidates, discoverer=discover, validator=validator,
        finalizer=finalizer,
    )


def read_manifest(directory: Path) -> dict:
    return json.loads((directory / "session.json").read_text(encoding="utf-8"))


def test_validated_interrupted_session_finalizes_and_records_result(tmp_path: Path) -> None:
    directory, output = make_session(tmp_path)
    assert output is not None
    seen_parts = []

    def finalizer(parts, destination):
        seen_parts.extend(parts)
        destination.write_bytes(b"recovered recording")
        return destination

    validations, result = finalize(
        directory, validator=Validator(directory), finalizer=finalizer
    )

    manifest = read_manifest(directory)
    assert validations is not None and validations[0].status == "passed"
    assert result.succeeded and result.status == "completed"
    assert result.validation_before == result.validation_after == "passed"
    assert result.output_path == str(output)
    assert output.read_bytes() == b"recovered recording"
    assert [path.name for path in seen_parts] == ["part-0001.flv"]
    assert manifest["status"] == "interrupted"
    assert manifest["recovery_performed"] is True
    assert manifest["part_count"] == 1
    assert manifest["output_path"] == str(output)
    assert manifest["finalization"] == {
        "error": None, "status": "completed",
        "input_decode": {"status": "unknown", "diagnostic_count": 0,
                         "diagnostic_codes": [], "count_capped": False},
    }


def test_validation_failure_prevents_any_finalization_mutation(tmp_path: Path) -> None:
    directory, _ = make_session(tmp_path)
    before = (directory / "session.json").read_bytes()

    def finalizer(*_):
        raise AssertionError("finalizer must not run")

    _, result = finalize(
        directory, validator=Validator(directory, pre_passes=False), finalizer=finalizer
    )

    assert result.status == "refused" and not result.attempted
    assert (directory / "session.json").read_bytes() == before


def test_active_session_is_refused_before_validation(tmp_path: Path) -> None:
    directory, _ = make_session(tmp_path, status="recording", finalization="pending")
    validator = Validator(directory)

    validations, result = finalize(
        directory, validator=validator,
        finalizer=lambda *_: (_ for _ in ()).throw(AssertionError()),
    )

    assert validations is None
    assert result.status == "refused" and validator.calls == 0
    assert read_manifest(directory)["finalization"]["status"] == "pending"


def test_existing_output_and_temporary_output_are_each_refused(tmp_path: Path) -> None:
    for artifact in ("output", "partial"):
        root = tmp_path / artifact
        root.mkdir()
        directory, output = make_session(root)
        assert output is not None
        path = output if artifact == "output" else output.with_name(".creator.partial.mp4")
        path.write_bytes(b"preserve")
        validator = Validator(directory)

        _, result = finalize(
            directory, validator=validator,
            finalizer=lambda *_: (_ for _ in ()).throw(AssertionError()),
        )

        assert result.status == "refused" and validator.calls == 0
        assert path.read_bytes() == b"preserve"


def test_missing_declared_output_requires_manual_finalize(tmp_path: Path) -> None:
    directory, _ = make_session(tmp_path, output_declared=False)
    validator = Validator(directory)

    _, result = finalize(directory, validator=validator, finalizer=lambda *_: None)

    assert result.status == "refused" and validator.calls == 0
    assert "manual tikrec finalize" in result.reason


def test_evidence_change_during_validation_refuses_before_action(tmp_path: Path) -> None:
    directory, _ = make_session(tmp_path)
    finalizer_calls = []

    def changing_validator(target, *, deep):
        path = Path(target) / "session.json"
        values = json.loads(path.read_text(encoding="utf-8"))
        values["error"] = "external change during validation"
        path.write_text(json.dumps(values), encoding="utf-8")
        return validation(Path(target))

    _, result = finalize(
        directory, validator=changing_validator,
        finalizer=lambda *_: finalizer_calls.append(True),
    )

    assert result.status == "refused" and not result.attempted
    assert "changed" in result.reason
    assert finalizer_calls == []
    assert read_manifest(directory)["recovery_performed"] is False


def test_finalizer_failure_is_recorded_and_parts_are_preserved(tmp_path: Path) -> None:
    directory, output = make_session(tmp_path)
    part = directory / "part-0001.flv"
    retained = part.read_bytes()

    def fail(*_):
        raise RuntimeError("signed https://cdn.invalid/secret")

    _, result = finalize(directory, validator=Validator(directory), finalizer=fail)

    manifest = read_manifest(directory)
    assert result.status == "failed" and result.attempted
    assert "cdn.invalid" not in manifest["finalization"]["error"]
    assert manifest["finalization"]["status"] == "failed"
    assert manifest["recovery_performed"] is True
    assert part.read_bytes() == retained
    assert output is not None and not output.exists()


def test_interruption_is_recorded_and_parts_are_preserved(tmp_path: Path) -> None:
    directory, _ = make_session(tmp_path)
    part = directory / "part-0001.flv"
    retained = part.read_bytes()

    def interrupt(*_):
        raise KeyboardInterrupt

    _, result = finalize(directory, validator=Validator(directory), finalizer=interrupt)

    manifest = read_manifest(directory)
    assert result.status == "interrupted" and result.attempted
    assert manifest["finalization"]["status"] == "interrupted"
    assert manifest["recovery_performed"] is True
    assert part.read_bytes() == retained


def test_empty_output_is_not_reported_as_success(tmp_path: Path) -> None:
    directory, _ = make_session(tmp_path)

    def empty_output(_, output):
        output.touch()
        return output

    _, result = finalize(
        directory, validator=Validator(directory), finalizer=empty_output
    )

    assert result.status == "failed" and not result.succeeded
    assert read_manifest(directory)["finalization"]["status"] == "failed"


def test_post_validation_failure_is_recorded_without_deleting_output(tmp_path: Path) -> None:
    directory, output = make_session(tmp_path)

    def finalizer(_, destination):
        destination.write_bytes(b"preserved diagnostic output")
        return destination

    _, result = finalize(
        directory, validator=Validator(directory, post_passes=False), finalizer=finalizer
    )

    assert result.status == "failed" and result.validation_after == "failed"
    assert output is not None and output.read_bytes() == b"preserved diagnostic output"
    assert read_manifest(directory)["finalization"]["status"] == "failed"


def test_parent_root_never_batch_finalizes_even_with_one_candidate(tmp_path: Path) -> None:
    directory, _ = make_session(tmp_path)
    validator = Validator(directory)

    validations, result = guided_finalize(
        tmp_path, discover(tmp_path), discoverer=discover, validator=validator,
        finalizer=lambda *_: (_ for _ in ()).throw(AssertionError()),
    )

    assert validations is None
    assert result.status == "refused" and not result.attempted
    assert "specific *.parts" in result.reason
    assert validator.calls == 0


def test_finalize_implies_validation_and_json_reports_outcome(tmp_path: Path) -> None:
    directory, output = make_session(tmp_path)
    config = tmp_path / "config.json"
    config.write_text(json.dumps({
        "schema_version": 1, "validation_mode": "deep",
    }), encoding="utf-8")
    validator = Validator(directory)
    stdout = StringIO()

    def finalizer(_, destination):
        destination.write_bytes(b"recording")
        return destination

    code = main(
        ["--config", str(config), "recover", str(directory), "--finalize", "--json"],
        recovery_discoverer=discover, validator=validator, finalizer=finalizer,
        stdout=stdout,
    )

    document = json.loads(stdout.getvalue())
    assert code == 0 and validator.calls == 2
    assert document["validation_requested"] is True
    assert document["candidates"][0]["validation"]["status"] == "passed"
    assert document["guided_finalization"]["status"] == "completed"
    assert document["guided_finalization"]["output_path"] == str(output)


def test_plain_output_explains_successful_destination(tmp_path: Path) -> None:
    directory, output = make_session(tmp_path)
    stdout = StringIO()

    def finalizer(_, destination):
        destination.write_bytes(b"recording")
        return destination

    code = main(
        ["recover", str(directory), "--finalize"],
        recovery_discoverer=discover, validator=Validator(directory), finalizer=finalizer,
        stdout=stdout,
    )

    assert code == 0
    assert f"Recovery completed — recovered recording written to {output}" in stdout.getvalue()
