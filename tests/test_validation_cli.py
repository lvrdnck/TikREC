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
        code = main(["validate", "recording.mp4"], validator=validator, stdout=stdout)

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
            ["validate", "missing.parts", "--json"], validator=validator, stdout=stdout
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

    def test_validate_missing_argument_uses_argparse_exit_two(self) -> None:
        self.assertEqual(main(["validate"], stderr=StringIO()), 2)


if __name__ == "__main__":
    unittest.main()
