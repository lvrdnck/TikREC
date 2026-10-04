"""Generated Windows media through the actual assembly primitive, never a queued task."""

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path
from uuid import uuid4

import pytest

from tests.capture_handoff_helpers import local_media
from tests.owned_process_helpers import managed_process
from tikrec.finalize import finalize_parts
from tikrec.media import inspect_media
from tikrec.part_validation import validate_part, verify_packet_dts
from tikrec.unpublished_assembly import UnpublishedAssembly
from tikrec.validation import validate_target

pytestmark = pytest.mark.skipif(os.name != "nt", reason="real Windows assembly evidence")


def guarded_factory(managed):
    """Preserve independent exact-job fixture guards and explicit attempt identity."""
    def make(session, attempt):
        owner = managed()
        owner.session_id, owner.attempt_token = session, attempt
        return owner
    return make


@pytest.mark.parametrize("different", [False, True], ids=["matching-copy", "differing-reencode"])
def test_generated_media_candidate_settings_hashes_and_validation(tmp_path, managed_process, different):
    source = tmp_path / "source"
    source.mkdir()
    parts = [source / "part-0001.flv", source / "part-0002.flv"]
    local_media(parts[0])
    if different:
        # Use the existing short local AVC/AAC fixture recipe at a second source size.
        subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc=size=80x64:rate=10",
                        "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100", "-t", "0.6",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-g", "3", "-c:a", "aac",
                        "-f", "flv", str(parts[1])], check=True, capture_output=True, timeout=30)
    else:
        shutil.copyfile(parts[0], parts[1])
    for name in ("connection-0001.raw", "connection-0001.arrivals.jsonl", "session.json", "connections.jsonl"):
        (source / name).write_bytes(("disposable fixture " + name).encode())
    hashes = lambda: {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in source.iterdir()}
    before = hashes()
    scope, final = tmp_path / "attempt", tmp_path / "requested-final.mp4"
    authorizations = []
    attempt = UnpublishedAssembly(session_id=str(uuid4()), attempt_token=str(uuid4()), inputs=parts[::-1],
        work_scope=scope, candidate=scope / "candidate.mp4", ffmpeg=Path(shutil.which("ffmpeg")).resolve(),
        ffprobe=Path(shutil.which("ffprobe")).resolve(),
        before_resume=lambda identity: authorizations.append(identity) or identity,
        process_factory=guarded_factory(managed_process))
    result = attempt.run()
    assert result.state == "candidate_ready" and result.publication == "unpublished"
    assert result.media_validation == "not_checked" and result.diagnostics_complete
    assert result.plan.stream_copy is not different
    assert len(result.children) == (3 if different else 1) == len(authorizations)
    assert all(c.owner.closed and c.evidence.state == "confirmed_exited" and
               c.evidence.active_processes == 0 and c.evidence.root_exit_code == 0 and
               c.evidence.stream_status == ("complete", "complete") for c in result.children)
    assert result.input_decode["status"] == ("clean" if different else "not_checked")
    for part in parts:
        problems, warnings = validate_part(part, "ffprobe", subprocess.run)
        assert not problems and not warnings, (problems, warnings)
    packets = subprocess.run(["ffprobe", "-v", "error", "-show_packets", "-show_entries",
                              "packet=stream_index,dts", "-of", "json", str(result.candidate)],
                             capture_output=True, text=True, check=True, timeout=30)
    assert not packets.stderr and not verify_packet_dts(packets.stdout)
    deep = validate_target(result.candidate, deep=True)
    assert deep.passed and deep.final_output_decode == "passed", deep.findings
    comparison = tmp_path / "synchronous-comparison.mp4"
    finalize_parts(parts[::-1], comparison)
    assert inspect_media(result.candidate) == inspect_media(comparison)
    assert validate_target(comparison, deep=True).passed
    def frames(path):
        probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_frames",
            "-show_entries", "frame=pts_time,duration_time,width,height", "-of", "json", str(path)],
            capture_output=True, text=True, check=True, timeout=30)
        assert not probe.stderr
        return [{k: frame[k] for k in ("pts_time", "duration_time", "width", "height") if k in frame}
                for frame in json.loads(probe.stdout)["frames"]]
    candidate_frames = frames(result.candidate)
    assert len(candidate_frames) == 12 and candidate_frames == frames(comparison)
    assert hashes() == before and not final.exists()
    report = dict(path="reencode" if different else "copy", source_sha256=before, unchanged=True,
                  candidate_sha256=hashlib.sha256(result.candidate.read_bytes()).hexdigest(),
                  candidate_bytes=result.candidate.stat().st_size,
                  frame_count=len(candidate_frames), synchronous_frame_timing_equal=True,
                  synchronous_bytes=comparison.stat().st_size, input_decode=result.input_decode,
                  plan=dict(stream_copy=result.plan.stream_copy, target_size=result.plan.target_size,
                            nominal_rate=str(result.plan.nominal_rate)),
                  process=[dict(phase=c.phase, pid=c.evidence.identity.pid,
                                created=c.evidence.identity.created, code=c.evidence.root_exit_code,
                                active=c.evidence.active_processes, streams=c.evidence.stream_status,
                                command=c.command) for c in result.children],
                  parts_valid=True, packet_dts_valid=True, deep_valid=True, final_absent=True)
    (tmp_path / "assembly-evidence.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


def test_candidate_occupied_during_authorization_is_preserved(tmp_path, managed_process):
    source = tmp_path / "source"
    source.mkdir()
    part = source / "part-0001.flv"
    local_media(part)
    before = hashlib.sha256(part.read_bytes()).hexdigest()
    scope = tmp_path / "attempt"
    def authorize(identity):
        (scope / "candidate.mp4").write_bytes(b"concurrent sibling ownership")
        return identity
    attempt = UnpublishedAssembly(session_id=str(uuid4()), attempt_token=str(uuid4()), inputs=[part],
        work_scope=scope, candidate=scope / "candidate.mp4", ffmpeg=Path(shutil.which("ffmpeg")).resolve(),
        ffprobe=Path(shutil.which("ffprobe")).resolve(), before_resume=authorize,
        process_factory=guarded_factory(managed_process))
    from tikrec.assembly_types import AssemblyError
    with pytest.raises(AssemblyError):
        attempt.run()
    assert attempt.candidate.read_bytes() == b"concurrent sibling ownership"
    assert hashlib.sha256(part.read_bytes()).hexdigest() == before
    assert attempt.result().children[0].evidence.state == "confirmed_exited"
