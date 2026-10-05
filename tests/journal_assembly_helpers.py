"""Disposable generated queued sessions and independent native test cleanup."""

import hashlib
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from tests.capture_handoff_helpers import authority, local_media, observations, reserve
from tests.owned_process_helpers import managed_process
from tikrec.source import iter_tags
from tikrec.tiktok import TikTokOfflineError, _ResolvedLiveUrl


def queue_media(owner, root, *, different=False, name="one", room="123"):
    """Use the real reconnect capture path to seal two FLVs and raw/control evidence."""
    sources = [root / (name + "-source1.flv"), root / (name + "-source2.flv")]
    first = local_media(sources[0])
    if different:
        subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc=size=80x64:rate=10",
            "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100", "-t", "0.6",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-g", "3", "-c:a", "aac",
            "-f", "flv", str(sources[1])], check=True, capture_output=True, timeout=30)
    else:
        shutil.copyfile(sources[0], sources[1])
    media = iter((first, sources[1].read_bytes()))
    resolutions = iter((_ResolvedLiveUrl("https://fixture.invalid/one.flv", 2, room_id=room),
        _ResolvedLiveUrl("https://fixture.invalid/two.flv", 2, room_id=room),
        TikTokOfflineError("fixture ended", room_id=room)))
    def resolver(_):
        value = next(resolutions)
        if isinstance(value, Exception):
            raise value
        return value
    def raw_source(_, raw):
        data = next(media)
        def chunks():
            for offset in range(0, len(data), 256):
                chunk = data[offset:offset + 256]
                raw.write(chunk)
                yield chunk
            raw.observe_read_end("eof")
        yield from iter_tags(chunks())
    bridge = reserve(owner, name, room=room, creator="creator" + room)
    options = observations(first, room=room)
    options.update(resolver=resolver, raw_tag_source=raw_source)
    assert bridge.run(**options).phase == "queued"
    assert len(tuple(Path(bridge.intent.parts_path).glob("part-*.flv"))) == 2
    return bridge, owner.journal.session(bridge.intent.session_id)


def original_hashes(root):
    """Hash fixture bytes without including later scratch files or SQLite state."""
    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob("*")
            if p.is_file() and p.name != ".tikrec-lifecycle.lock"}


@pytest.fixture
def connected(tmp_path, managed_process, monkeypatch, request):
    """Keep every exact owner reachable until evidence assertions finish."""
    from tikrec.journal_assembly import JournalAssembly
    different = getattr(request, "param", False)
    with authority(tmp_path) as owner:
        bridge, original = queue_media(owner, tmp_path, different=different)
        sentinel = owner.root / "unrelated.bin"
        sentinel.write_bytes(b"unrelated evidence unchanged")
        before = original_hashes(owner.root)
        before.update({str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                       for p in tmp_path.glob("one-source*.flv")})
        def create(sid, token):
            process = managed_process()
            process.session_id, process.attempt_token = sid, token
            return process
        adapter = JournalAssembly(owner, ffmpeg=Path(shutil.which("ffmpeg")).resolve(),
            ffprobe=Path(shutil.which("ffprobe")).resolve(), process_factory=create)
        yield adapter, bridge, original, before
        monkeypatch.undo()
        adapter.coordinator._fault = lambda _: None
        owner.journal._fault = None
        adapter.close()
        assert {p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in before} == before
        current = owner.journal.session(original["id"])
        for field in ("seal", "seal_hash", "artifacts", "rooms"):
            assert current[field] == original[field]
        assert not Path(bridge.intent.output_path).exists()
        # Failed/ambiguous production owners are deliberately retained. Only
        # these disposable fixtures release pins after independent job exit.
        runner = adapter.coordinator
        assert all(c["process"].closed for c in runner.children)
        if runner.scratch is not None:
            for held in [*runner.scratch.artifacts.values(), runner.scratch.workspace]:
                if held is not None:
                    held.close()
        adapter.close()
