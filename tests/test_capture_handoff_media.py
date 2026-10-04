"""Deep validation of valid fixture media through the unchanged synchronous path."""

import os
import subprocess

import pytest

from tests.capture_handoff_helpers import authority, contents, local_media, observations, reserve
from tikrec.live import capture_live
from tikrec.part_validation import validate_part
from tikrec.validation import validate_target

pytestmark = pytest.mark.skipif(os.name != "nt", reason="requires native Windows fixture capture")


def test_retained_fixture_and_separate_completed_synchronous_media_validate(tmp_path):
    data = local_media(tmp_path / "fixture.flv")
    with authority(tmp_path) as owner:
        bridge = reserve(owner)
        bridge.run(**observations(data))
        part = owner.root / "one.parts/part-0001.flv"
        problems, warnings = validate_part(part, "ffprobe", subprocess.run)
        assert not problems and not warnings
        queued_before = contents(owner.root)
        output = tmp_path / "synchronous.mp4"
        options = observations(data)
        options.pop("media_inspector")
        result = capture_live("https://www.tiktok.com/@creator/live",
                              parts_directory=output.with_suffix(".parts"), output_path=output,
                              raw_copy_dir=output.with_suffix(".parts"), **options)
        assert result.output_path == output and output.exists()
        checked = validate_target(output.with_suffix(".parts"), deep=True)
        assert checked.passed, checked.findings
        assert checked.retained_media_checks == "passed" and checked.final_output_decode == "passed"
        assert contents(owner.root) == queued_before
