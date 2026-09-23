"""Manual finalization records fixed decoder evidence when available."""

import json

from tikrec.cli_manifest import _finish_recovery
from tikrec.decode_diagnostics import input_decode_health
from tikrec.manifest import SessionManifest


def test_manual_recovery_keeps_lifecycle_and_bounded_health(tmp_path):
    parts_dir = tmp_path / "recording.parts"
    parts_dir.mkdir()
    part = parts_dir / "part-0001.flv"
    part.write_bytes(b"retained")
    output = tmp_path / "recording.mp4"
    output.write_bytes(b"finished")
    manifest = SessionManifest(parts_dir, output, "direct_flv")
    manifest.start()
    manifest.complete((part,), interrupted=True, finalization_status="not_started")
    manifest.mark_recovery(output, (part,))
    _finish_recovery(manifest, (part,), "completed", lambda _: None,
                     output_path=output,
                     input_decode=input_decode_health("degraded", 1, ("h264_macroblock",)))
    values = json.loads(manifest.path.read_text(encoding="utf-8"))
    assert values["status"] == "interrupted"
    assert values["finalization"]["input_decode"]["status"] == "degraded"
