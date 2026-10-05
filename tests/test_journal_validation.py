"""New connected validation retains the exact unpublished candidate and inputs."""

import hashlib
import json
import os
import shutil
from pathlib import Path

import pytest

from tests.journal_assembly_helpers import queue_media, original_hashes, managed_process
from tests.capture_handoff_helpers import authority
from tikrec.journal_validation import JournalValidation

pytestmark = pytest.mark.skipif(os.name != "nt", reason="native Windows validation")


@pytest.fixture
def validated(tmp_path, managed_process, monkeypatch, request):
    """Keep live protection until assertions and independent native cleanup finish."""
    with authority(tmp_path) as owner:
        bridge, original = queue_media(owner, tmp_path, different=getattr(request, "param", False))
        (owner.root / "unrelated.bin").write_bytes(b"unchanged sentinel")
        before = original_hashes(owner.root)
        h_before = owner.journal._read(lambda db: [tuple(row) for row in
            db.execute("SELECT * FROM operations WHERE kind='handoff' ORDER BY id")])
        before.update({str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in tmp_path.glob("*-source*.flv")})
        def factory(sid, token):
            process = managed_process()
            process.session_id, process.attempt_token = sid, token
            return process
        adapter = JournalValidation(owner, ffmpeg=Path(shutil.which("ffmpeg")).resolve(),
            ffprobe=Path(shutil.which("ffprobe")).resolve(), process_factory=factory)
        yield adapter, bridge, original, before
        monkeypatch.undo()
        runner = adapter.coordinator
        runner._fault, owner.journal._fault = lambda _: None, None
        adapter.close()
        assert {p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in before} == before
        current = owner.journal.session(original["id"])
        for field in ("seal", "seal_hash", "artifacts", "rooms"):
            assert current[field] == original[field]
        assert owner.journal._read(lambda db: [tuple(row) for row in
            db.execute("SELECT * FROM operations WHERE kind='handoff' AND id=?", (h_before[0][0],))]) == h_before
        assert not Path(bridge.intent.output_path).exists()
        assert all(c["process"].closed for c in runner.children)
        if runner.scratch:
            for held in [*runner.scratch.artifacts.values(), runner.scratch.workspace]:
                if held is not None:
                    held.close()
        if runner.guard is not None:
            runner.guard.close()


@pytest.mark.parametrize("validated", [False, True], indirect=True, ids=["copy", "libx264"])
def test_same_attempt_validation_is_durable_unpublished_and_pinned(validated):
    adapter, bridge, original, before = validated
    result = adapter.run()
    runner = adapter.coordinator
    receipt = runner.journal.validation(runner.token)
    candidate = runner.journal.scratch(runner.token)["candidate"]
    assert result["passed"] and receipt["evidence"]["report"]["passed"]
    assert receipt["binding"]["candidate"] == candidate
    assert receipt["binding"]["session_id"] == original["id"]
    assert candidate["publication"] == "unpublished" and candidate["validation"] == "not_checked"
    assert runner.guard.closed is False
    assert runner.scratch.protection_evidence()["artifacts_retained"]
    assert len(runner.journal.status()["units"]) == 1
    assert runner.journal.session(original["id"])["task"]["state"] == "running"
    assert not Path(bridge.intent.output_path).exists()
    assert {p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in before} == before
    assert len(receipt["evidence"]["children"]) == 3
    assert all(c["process"].closed for c in runner.children)
    with pytest.raises(Exception) as caught:
        runner.run_child(adapter.assembly.ffprobe, ["-version"], cwd=runner.authority.root,
                         phase="arbitrary", timeout=5)
    assert "candidate-ready" in str(caught.value.original)
    (runner.authority.root.parent / "validation-media-evidence.json").write_text(
        json.dumps({"receipt": receipt, "hashes": before, "unchanged": True,
                    "final_absent": True, "pins": runner.journal.status()}, indent=2))
