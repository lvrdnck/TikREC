from __future__ import annotations

import unittest

from tikrec.validation_report import ValidationFinding, ValidationResult, render_validation


class ValidationReportTests(unittest.TestCase):
    def test_human_report_separates_state_and_collected_findings(self) -> None:
        result = ValidationResult(
            "recording.parts", "session", True, False,
            "failed", "interrupted", "missing", 2,
            (
                ValidationFinding("error", "part_decode", "decoder failed", "part-0002.flv"),
                ValidationFinding("warning", "output_missing", "output is unavailable"),
            ),
        )

        report = render_validation(result)

        self.assertIn("Validation failed", report)
        self.assertIn("Media integrity: failed", report)
        self.assertIn("Validation mode: deep", report)
        self.assertIn("Session completeness: interrupted", report)
        self.assertIn("Errors:\n- [part_decode]", report)
        self.assertIn("Warnings:\n- [output_missing]", report)

    def test_json_values_include_stable_finding_fields(self) -> None:
        result = ValidationResult(
            "recording.mp4", "output", False, True,
            "passed", "not_applicable", "present", 0,
            (ValidationFinding("warning", "output_audio_missing", "no audio"),),
        )

        values = result.as_dict()

        self.assertTrue(values["passed"])
        self.assertEqual(values["findings"][0]["code"], "output_audio_missing")
        self.assertIn("path", values["findings"][0])


if __name__ == "__main__":
    unittest.main()
