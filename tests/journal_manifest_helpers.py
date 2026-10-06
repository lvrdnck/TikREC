"""Generated connected completion fixtures with independent owner cleanup."""

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from tests.capture_handoff_helpers import authority, local_media, reserve, observations
from tests.journal_assembly_helpers import queue_media, original_hashes, managed_process
from tikrec.journal_manifest import JournalManifest


@pytest.fixture
def completing(tmp_path, managed_process, monkeypatch, request):
    """Preserve original controls through held-object checks, including failed moves."""
    with authority(tmp_path) as owner:
        param = getattr(request, "param", False)
        if param == "interrupted":
            from tikrec.source import iter_tags
            data = local_media(tmp_path / "one-source1.flv")
            bridge = reserve(owner)
            def source(_, raw):
                raw.write(data)
                yield from iter_tags((data,))
                bridge.stop()
            assert bridge.run(**observations(data, source=source)).phase == 'queued'
            original = owner.journal.session(bridge.intent.session_id)
        else:
            bridge, original = queue_media(owner, tmp_path, different=param)
        (owner.root / "unrelated.bin").write_bytes(b"unchanged unrelated evidence")
        manifest = Path(bridge.intent.parts_path) / "session.json"
        original_bytes = manifest.read_bytes()
        before = original_hashes(owner.root)
        before.update({str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in tmp_path.glob("*-source*.flv")})
        h = owner.journal._read(lambda db: [tuple(r) for r in db.execute("SELECT * FROM operations WHERE kind='handoff'")])
        def create(sid, token):
            process = managed_process()
            process.session_id, process.attempt_token = sid, token
            return process
        adapter = JournalManifest(owner, ffmpeg=Path(shutil.which("ffmpeg")).resolve(),
            ffprobe=Path(shutil.which("ffprobe")).resolve(), process_factory=create)
        yield adapter, bridge, original, before, original_bytes
        monkeypatch.undo()
        runner = adapter.coordinator
        runner._fault, owner.journal._fault = lambda _: None, None
        assert not adapter.close()
        for p, value in before.items():
            if p == str(manifest):
                held = next(x for x in runner.guard.files if x.path.name == "session.json" or
                            x.initial == next(a.stamp for a in runner.guard.seal.artifacts
                                              if a.identity.components[-1] == "session.json"))
                assert held.read_control() == original_bytes
            else:
                assert hashlib.sha256(Path(p).read_bytes()).hexdigest() == value
        current = owner.journal.session(original["id"])
        for field in ("seal", "seal_hash", "artifacts", "rooms"):
            assert current[field] == original[field]
        assert owner.journal._read(lambda db: [tuple(r) for r in db.execute(
            "SELECT * FROM operations WHERE kind='handoff' AND id=?", (h[0][0],))]) == h
        assert current["task"]["state"] == "running" and owner.journal.status()["units"]
        assert all(c["process"].closed for c in runner.children)
        if adapter.capability and adapter.capability.stage:
            adapter.capability.stage.close()
        if runner.scratch:
            for held in [*runner.scratch.artifacts.values(), runner.scratch.workspace]:
                if held:
                    held.close()
        if runner.guard:
            runner.guard.close()


def completed_values(adapter):
    """Read installed bytes through the exact retained successor descriptor."""
    return json.loads(adapter.capability.stage.read_control())
