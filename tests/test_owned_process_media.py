"""One contained FFmpeg operation on generated scratch media; no journal/publication."""

import hashlib
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from tests.capture_handoff_helpers import local_media
from tests.owned_process_helpers import managed_process
from tikrec.finalize import _build_ffmpeg_command, _write_concat_manifest
from tikrec.part_validation import validate_part
from tikrec.validation import validate_target

pytestmark = pytest.mark.skipif(os.name != "nt", reason="real Windows FFmpeg ownership")


def test_owned_ffmpeg_scratch_operation_preserves_input_and_validates(tmp_path, managed_process):
    source = tmp_path / "part-0001.flv"
    local_media(source)
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    scratch = tmp_path / "separate-output"
    scratch.mkdir()
    manifest = _write_concat_manifest((source,), scratch)
    output = scratch / "candidate.mp4"
    executable = Path(shutil.which("ffmpeg")).resolve()
    command = _build_ffmpeg_command((source,), output, ffmpeg=executable, manifest=manifest, target_size=None)
    owner = managed_process()
    owner.start(executable, command[1:], cwd=scratch, before_resume=lambda value: value)
    result = owner.wait(30)
    assert result.state == "confirmed_exited" and result.root_exit_code == 0 and result.active_processes == 0
    assert owner.close().state == "confirmed_exited"
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before
    problems, warnings = validate_part(source, "ffprobe", subprocess.run)
    assert not problems and not warnings
    validated = validate_target(output, deep=True)
    assert validated.passed and validated.final_output_decode == "passed", validated.findings
    # Durable journal claims and media success receipts are deliberately absent.
    assert not list(tmp_path.rglob("*.sqlite3")) and not list(tmp_path.rglob("session.json"))
