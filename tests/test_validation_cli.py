from __future__ import annotations

import json
from io import StringIO
from pathlib import Path
import unittest

from tikrec.cli import main
from tikrec.validation_report import ValidationFinding, ValidationResult


class ValidationCliTests(unittest.TestCase):
    def test_validate_prints_human_report_and_returns_zero_for_success(self) -> None:
        targets: list[Path] = []

        def validator(target: Path, **_: object) -> ValidationResult:
            targets.append(target)
            return ValidationResult(
                str(target), "output", False, True, "passed", "not_applicable", "present", 0, (),
            )

        stdout = StringIO()
        code = main([
            "validate", "recording.mp4", "--standard",
        ], validator=validator, stdout=stdout)

        self.assertEqual(code, 0)
        self.assertEqual(targets, [Path("recording.mp4")])
        self.assertIn("Validation passed", stdout.getvalue())

    def test_validate_json_is_machine_readable_and_failure_returns_one(self) -> None:
        def validator(target: Path, **_: object) -> ValidationResult:
            return ValidationResult(
                str(target), "missing", False, False,
                "not_checked", "not_applicable", "missing", 0,
                (ValidationFinding("error", "target_missing", "target does not exist", str(target)),),
            )

        stdout = StringIO()
        code = main(
            ["validate", "missing.parts", "--standard", "--json"],
            validator=validator, stdout=stdout,
        )

        values = json.loads(stdout.getvalue())
        self.assertEqual(code, 1)
        self.assertFalse(values["passed"])
        self.assertFalse(values["deep"])
        self.assertEqual(values["findings"][0]["code"], "target_missing")

    def test_deep_flag_is_passed_to_the_validator(self) -> None:
        modes: list[bool] = []

        def validator(target: Path, *, deep: bool) -> ValidationResult:
            modes.append(deep)
            return ValidationResult(
                str(target), "output", deep, True,
                "passed", "not_applicable", "present", 0, (),
            )

        code = main(
            ["validate", "recording.mp4", "--deep"],
            validator=validator,
            stdout=StringIO(),
        )

        self.assertEqual(code, 0)
        self.assertEqual(modes, [True])

    def test_configured_modes_and_explicit_precedence(self) -> None:
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "config.json"
            modes: list[bool] = []

            def validator(target: Path, *, deep: bool) -> ValidationResult:
                modes.append(deep)
                return ValidationResult(
                    str(target), "output", deep, True,
                    "passed", "not_applicable", "present", 0, (),
                )

            for configured, flag, expected in (
                ("deep", [], True),
                ("standard", [], False),
                ("standard", ["--deep"], True),
                ("deep", ["--standard"], False),
            ):
                path.write_text(json.dumps({
                    "schema_version": 1, "validation_mode": configured,
                }), encoding="utf-8")
                code = main(
                    ["--config", str(path), "validate", "recording.mp4", *flag],
                    validator=validator, stdout=StringIO(),
                )
                self.assertEqual(code, 0)
                self.assertEqual(modes[-1], expected)

    def test_missing_setting_uses_built_in_standard(self) -> None:
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "missing.json"
            modes: list[bool] = []

            def validator(target: Path, *, deep: bool) -> ValidationResult:
                modes.append(deep)
                return ValidationResult(
                    str(target), "output", deep, True,
                    "passed", "not_applicable", "present", 0, (),
                )

            self.assertEqual(main([
                "--config", str(path), "validate", "recording.mp4",
            ], validator=validator, stdout=StringIO()), 0)
            self.assertEqual(modes, [False])

    def test_explicit_mode_skips_malformed_configuration(self) -> None:
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "config.json"
            path.write_text("{", encoding="utf-8")
            modes: list[bool] = []

            def validator(target: Path, *, deep: bool) -> ValidationResult:
                modes.append(deep)
                return ValidationResult(
                    str(target), "output", deep, True,
                    "passed", "not_applicable", "present", 0, (),
                )

            for flag, expected in (("--deep", True), ("--standard", False)):
                self.assertEqual(main([
                    "--config", str(path), "validate", "recording.mp4", flag,
                ], validator=validator, stdout=StringIO()), 0)
                self.assertEqual(modes[-1], expected)

    def test_implicit_mode_fails_on_malformed_configuration(self) -> None:
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "config.json"
            path.write_text("{", encoding="utf-8")
            stderr = StringIO()
            code = main([
                "--config", str(path), "validate", "recording.mp4",
            ], validator=lambda *_args, **_kwargs: self.fail("validator must not run"),
               stderr=stderr)
            self.assertEqual(code, 1)
            self.assertIn("invalid configuration", stderr.getvalue())

    def test_mode_flags_are_mutually_exclusive(self) -> None:
        self.assertEqual(main([
            "validate", "recording.mp4", "--deep", "--standard",
        ], stderr=StringIO()), 2)

    def test_json_and_human_reports_use_effective_mode(self) -> None:
        def validator(target: Path, *, deep: bool) -> ValidationResult:
            return ValidationResult(
                str(target), "output", deep, True,
                "passed", "not_applicable", "present", 0, (),
            )

        stdout = StringIO()
        self.assertEqual(main([
            "validate", "recording.mp4", "--deep", "--json",
        ], validator=validator, stdout=stdout), 0)
        self.assertTrue(json.loads(stdout.getvalue())["deep"])
        stdout = StringIO()
        self.assertEqual(main([
            "validate", "recording.mp4", "--standard",
        ], validator=validator, stdout=stdout), 0)
        self.assertIn("Validation mode: standard", stdout.getvalue())

    def test_validate_missing_argument_uses_argparse_exit_two(self) -> None:
        self.assertEqual(main(["validate"], stderr=StringIO()), 2)


if __name__ == "__main__":
    unittest.main()
