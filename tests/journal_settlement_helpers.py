"""Disposable complete-lifecycle fixtures; cleanup is independent of product claims."""

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from tests.capture_handoff_helpers import authority, local_media, observations, reserve
from tests.journal_assembly_helpers import queue_media, original_hashes, managed_process


def adapter_for(owner, managed_process):
    """Create the explicit success adapter with separately tracked native children."""
    from tikrec.journal_settlement import JournalSettlement
    def create(sid, token):
        process = managed_process()
        process.session_id, process.attempt_token = sid, token
        return process
    return JournalSettlement(owner, ffmpeg=Path(shutil.which('ffmpeg')).resolve(),
        ffprobe=Path(shutil.which('ffprobe')).resolve(), process_factory=create)


def independent_cleanup(adapter):
    """Release disposable exact objects after assertions without settling product state."""
    cap = adapter.capability
    if cap is not None:
        for reader in cap.readers:
            reader.cleanup()
    runner = adapter.coordinator
    if getattr(runner, 'manifest_owner', None):
        runner.manifest_owner.cleanup_fence()
    for child in runner.children:
        assert child['process'].close(5).state == 'confirmed_exited'
        assert child['process'].closed
    if runner.scratch:
        for held in [*runner.scratch.artifacts.values(), runner.scratch.workspace]:
            if held is not None:
                held.close()
    if runner.guard:
        runner.guard.close()


@pytest.fixture
def settling(tmp_path, managed_process, monkeypatch, request):
    """Keep raw/capture/original-H evidence available through independent teardown."""
    with authority(tmp_path) as owner:
        mode = getattr(request, 'param', False)
        if mode == 'interrupted':
            from tikrec.source import iter_tags
            data = local_media(tmp_path / 'one-source1.flv')
            bridge = reserve(owner)
            def source(_, raw):
                raw.write(data)
                yield from iter_tags((data,))
                bridge.stop()
            assert bridge.run(**observations(data, source=source)).phase == 'queued'
            original = owner.journal.session(bridge.intent.session_id)
        else:
            bridge, original = queue_media(owner, tmp_path, different=mode)
        (owner.root / 'unrelated.bin').write_bytes(b'unchanged unrelated evidence')
        manifest = Path(bridge.intent.parts_path) / 'session.json'
        raw = manifest.read_bytes()
        before = original_hashes(owner.root)
        before.update({str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                       for p in tmp_path.glob('*-source*.flv')})
        h = owner.journal._read(lambda db: [tuple(r) for r in db.execute(
            "SELECT * FROM operations WHERE kind='handoff'")])
        adapter = adapter_for(owner, managed_process)
        yield adapter, bridge, original, before, raw
        monkeypatch.undo()
        runner = adapter.coordinator
        runner._fault, owner.journal._fault = lambda _: None, None
        independent_cleanup(adapter)
        history = manifest.parent / f'.tikrec-manifest-{runner.token}.original.json'
        for path, expected in before.items():
            actual = history if path == str(manifest) and history.exists() else Path(path)
            assert hashlib.sha256(actual.read_bytes()).hexdigest() == expected
        current = owner.journal.session(original['id'])
        for key in ('seal', 'seal_hash', 'intent', 'generation', 'origin_slot'):
            assert current[key] == original[key]
        assert owner.journal._read(lambda db: [tuple(r) for r in db.execute(
            "SELECT * FROM operations WHERE kind='handoff' AND id=?", (h[0][0],))]) == h
        if history.exists():
            from tikrec.manifest_successor_values import unpacked
            assert history.read_bytes() == raw
            record = owner.journal.manifest_completion(runner.token)
            successor = manifest
            if not manifest.exists():
                # Failed pre-install native work preserves complete staged bytes.
                cap = runner.manifest_owner
                assert cap.preserved and cap.written and not cap.installed
                assert [step['phase'] for step in record['steps']] == ['staged', 'preserved']
                assert record['steps'][0]['evidence']['required_flushed']
                successor = cap.stage.path
            assert successor.read_bytes() == unpacked(record['binding']['successor'])
            old, current = json.loads(raw), json.loads(successor.read_bytes())
            assert all(current[k] == old[k] for k in old.keys() - {'finalization', 'media'})
