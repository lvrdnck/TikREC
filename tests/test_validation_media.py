"""Output-only inspection and full decoding remain distinct facts."""

from tests.test_validation import ProbeRunner
from tikrec.validation import validate_target


def test_failed_full_output_decode_does_not_erase_passed_inspection(tmp_path):
    output = tmp_path / "recording.mp4"
    output.write_bytes(b"media")
    runner = ProbeRunner()
    runner.decode_errors[output.name] = "decoder rejected frame"
    result = validate_target(output, deep=True, runner=runner)
    assert not result.passed
    assert result.final_output_inspection == "passed"
    assert result.final_output_decode == "failed"
    assert result.retained_media_checks == "not_checked"
