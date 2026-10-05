"""Generated sealed sessions exercise the NEW durable assembly adapter itself."""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests.journal_assembly_helpers import connected, managed_process
from tikrec.finalize import finalize_parts
from tikrec.media import inspect_media
from tikrec.part_validation import validate_part, verify_packet_dts
from tikrec.validation import validate_target

pytestmark = pytest.mark.skipif(os.name != "nt", reason="actual connected Windows media evidence")


def frames(path):
    """Compare passthrough timing and dimensions with accepted synchronous output."""
    response = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_frames",
        "-show_entries", "frame=pts_time,duration_time,width,height", "-of", "json", str(path)],
        capture_output=True, text=True, check=True, timeout=30)
    assert not response.stderr
    return [{k: frame[k] for k in ("pts_time", "duration_time", "width", "height") if k in frame}
            for frame in json.loads(response.stdout)["frames"]]


@pytest.mark.parametrize("connected", [False, True], indirect=True, ids=["copy", "libx264"])
def test_connected_generated_media_hashes_validation_and_frame_timing(connected):
    adapter, bridge, original, before = connected
    result = adapter.run()
    runner = adapter.coordinator
    assert result.state == "candidate_ready" and result.publication == "unpublished"
    assert result.media_validation == "not_checked" and result.diagnostics_complete
    assert len(result.children) == (1 if result.plan.stream_copy else 3)
    assert result.input_decode["status"] == ("not_checked" if result.plan.stream_copy else "clean")
    assert all(c.owner.closed and c.evidence.state == "confirmed_exited"
        and c.evidence.active_processes == 0 and c.evidence.root_exit_code == 0
        and c.evidence.stream_status == ("complete", "complete") for c in result.children)
    record = runner.journal.scratch(runner.token)
    assert record["candidate"]["publication"] == "unpublished"
    assert record["candidate"]["validation"] == "not_checked"
    assert record["candidate"]["seal_hash"] == original["seal_hash"]
    assert record["candidate"]["execution"]["input_decode"] == ("unknown" if result.plan.stream_copy else "clean")
    assert len(runner.journal.status()["units"]) == 1
    assert runner.journal.session(original["id"])["phase"] == "running"
    # Local close releases only proven native controls; durable unit/pins and
    # unfinished running task remain. Validation below is disposable test evidence.
    assert adapter.close()
    for part in result.plan.parts:
        problems, warnings = validate_part(part, "ffprobe", subprocess.run)
        assert not problems and not warnings, (problems, warnings)
    checked_parts = validate_target(Path(bridge.intent.parts_path))
    assert checked_parts.retained_media_checks == "passed"
    # The legacy validator expects a completed session to have finalized output;
    # this deliberately unchanged capture-only pending manifest cannot satisfy it.
    assert {f.code for f in checked_parts.findings} == {"manifest_state_inconsistent", "output_missing"}
    response = subprocess.run(["ffprobe", "-v", "error", "-show_packets", "-show_entries",
        "packet=stream_index,dts", "-of", "json", str(result.candidate)],
        capture_output=True, text=True, check=True, timeout=30)
    assert not response.stderr and not verify_packet_dts(response.stdout)
    deep = validate_target(result.candidate, deep=True)
    assert deep.passed and deep.final_output_decode == "passed", deep.findings
    comparison = runner.authority.root.parent / "synchronous-comparison.mp4"
    finalize_parts(result.plan.parts[::-1], comparison)
    assert inspect_media(result.candidate) == inspect_media(comparison)
    candidate_frames = frames(result.candidate)
    assert len(candidate_frames) == 12 and candidate_frames == frames(comparison)
    assert validate_target(comparison, deep=True).passed
    assert {p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in before} == before
    assert not Path(bridge.intent.output_path).exists()
    assert runner.journal.scratch(runner.token)["candidate"]["validation"] == "not_checked"
    report = {"path": "copy" if result.plan.stream_copy else "libx264", "original_hashes": before,
        "unchanged": True, "candidate": record["candidate"], "original_H": original["seal"],
        "frames": candidate_frames, "synchronous_frame_timing_equal": True,
        "parts_valid": True, "pending_manifest_findings": [f.code for f in checked_parts.findings],
        "packet_dts_valid": True, "deep_valid": True,
        "final_absent": True, "units": runner.journal.status()["units"],
        "children": [{"phase": c.phase, "command": c.command, "code": c.evidence.root_exit_code,
            "active": c.evidence.active_processes, "pid": c.evidence.identity.pid,
            "created": c.evidence.identity.created, "streams": c.evidence.stream_status}
            for c in result.children]}
    (runner.authority.root.parent / "connected-media-evidence.json").write_text(json.dumps(report, indent=2))


@pytest.mark.parametrize("connected", [True], indirect=True)
def test_degraded_tail_beyond_native_prefix_is_preserved_not_repaired(connected, monkeypatch):
    import tikrec.journal_assembly as module
    adapter, _, _, _ = connected
    build = module._build_ffmpeg_command
    diagnostic = b"warning\n" * 4000 + b"[h264 @ 0x1] corrupt slice"
    def command(*args, **kwargs):
        media_command = build(*args, **kwargs)
        code = "import subprocess,sys;code=subprocess.call(" + repr(media_command) + ");" \
            "sys.stderr.buffer.write(b'warning\\n'*4000+b'[h264 @ 0x1] corrupt slice');sys.exit(code)"
        return [str(Path(sys._base_executable)), "-c", code]
    monkeypatch.setattr(module, "_build_ffmpeg_command", command)
    result = adapter.run()
    assert result.state == "candidate_ready" and result.input_decode["status"] == "degraded"
    assert result.media_validation == "not_checked" and result.diagnostics_complete
    runner = adapter.coordinator
    child = runner.journal.owned_attempt(runner.token)["child"]
    assert child["diagnostics"]["complete"] and child["diagnostics"]["dropped"][1] > 0
    assert child["diagnostics"]["counts"]["stderr"] >= len(diagnostic)
    assert runner.journal.scratch(runner.token)["candidate"]["execution"]["input_decode"] == "degraded"
    assert adapter.close()
    assert validate_target(result.candidate, deep=True).passed
