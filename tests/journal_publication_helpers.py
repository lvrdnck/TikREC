"""Disposable connected publication fixture with independent retained-owner cleanup."""

import hashlib
import os
import shutil
from pathlib import Path

import pytest

from tests.capture_handoff_helpers import authority
from tests.journal_assembly_helpers import queue_media, original_hashes, managed_process
from tikrec.journal_publication import JournalPublication


@pytest.fixture
def publishing(tmp_path, managed_process, monkeypatch, request):
    """Assert immutable original evidence before independently releasing fixture pins."""
    with authority(tmp_path) as owner:
        bridge, original = queue_media(owner, tmp_path, different=getattr(request, "param", False))
        (owner.root / "unrelated.bin").write_bytes(b"preserved sentinel")
        before = original_hashes(owner.root)
        before.update({str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in tmp_path.glob("*-source*.flv")})
        h = owner.journal._read(lambda db: [tuple(r) for r in db.execute("SELECT * FROM operations WHERE kind='handoff'")])
        def factory(sid, token):
            process = managed_process()
            process.session_id, process.attempt_token = sid, token
            return process
        adapter = JournalPublication(owner, ffmpeg=Path(shutil.which("ffmpeg")).resolve(),
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
        assert owner.journal._read(lambda db: [tuple(r) for r in db.execute(
            "SELECT * FROM operations WHERE kind='handoff' AND id=?", (h[0][0],))]) == h
        assert current["task"]["state"] == "running" and len(owner.journal.status()["units"]) >= 1
        assert all(c["process"].closed for c in runner.children)
        if runner.scratch:
            for held in [*runner.scratch.artifacts.values(), runner.scratch.workspace]:
                if held is not None:
                    held.close()
        if runner.guard:
            runner.guard.close()


def held_hash(held):
    """Read the original descriptor: ordinary reopening conflicts with DELETE ownership."""
    os.lseek(held.fd, 0, os.SEEK_SET)
    value = hashlib.sha256()
    while chunk := os.read(held.fd, 65536):
        value.update(chunk)
    return value.hexdigest()
