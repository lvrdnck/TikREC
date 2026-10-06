"""Manifest completion preserves capture truth and retains all accounting."""

import base64
import json
import os

import pytest

from tests.journal_manifest_helpers import completing, completed_values
from tests.journal_assembly_helpers import managed_process
from tests.journal_publication_helpers import held_hash, publishing

pytestmark = pytest.mark.skipif(os.name != "nt", reason="native Windows completion")


@pytest.mark.parametrize("completing", [False, True], indirect=True, ids=["copy", "libx264"])
def test_connected_manifest_completion_preserves_capture_and_exact_output(completing):
    adapter, bridge, original, before, raw = completing
    evidence = adapter.run()
    runner, cap = adapter.coordinator, adapter.capability
    record = runner.journal.manifest_completion(runner.token)
    values, old = completed_values(adapter), json.loads(raw)
    assert evidence == record["steps"][-1]["evidence"]
    assert evidence["state"] == "installed" and evidence["required_flushed"]
    assert base64.b64decode(record["binding"]["predecessor"]["bytes"]) == raw
    assert cap.predecessor.read_control() == raw and cap.history.exists()
    for key in old.keys() - {"finalization", "media"}:
        assert values[key] == old[key]
    assert values["finalization"]["status"] == "completed"
    assert values["finalization"]["error"] == old["finalization"]["error"]
    assert values["finalization"]["input_decode"] == adapter.publication.validation.assembly.result().input_decode
    assert values["media"] == {"video_codec": "h264", "audio_codec": "aac", "width": 64 if adapter.publication.validation.assembly.plan.stream_copy else 80, "height": 64}
    candidate = runner.journal.scratch(runner.token)["candidate"]
    assert held_hash(runner.scratch.artifacts["candidate.mp4"]) == candidate["sha256"]
    assert runner.guard.revalidate().seal_hash == original["seal_hash"]
    assert runner.journal.session(original["id"])["task"]["state"] == "running"
    assert not adapter.close() and cap.stage.handle is not None and cap.predecessor.handle is not None
    with pytest.raises(Exception):
        adapter.run()
    with pytest.raises(Exception):
        cap.complete()


@pytest.mark.parametrize('completing', ['interrupted'], indirect=True)
def test_completed_output_preserves_interrupted_capture(completing):
    adapter, _, _, _, raw = completing
    old = json.loads(raw)
    assert old['status'] == 'interrupted' and old['interrupted']
    assert old['error'] is None
    adapter.run()
    values = completed_values(adapter)
    for key in old.keys() - {'finalization', 'media'}:
        assert values[key] == old[key]
    assert values['finalization']['status'] == 'completed'
    assert values['finalization']['input_decode']['status'] == 'not_checked'


@pytest.mark.parametrize('completing', [True], indirect=True)
def test_degraded_input_classification_survives_clean_owned_output(completing, monkeypatch):
    import sys
    from pathlib import Path
    from tikrec import journal_assembly as module
    adapter, _, _, _, _ = completing
    build = module._build_ffmpeg_command
    def command(*args, **kwargs):
        media_command = build(*args, **kwargs)
        code = "import subprocess,sys;code=subprocess.call(" + repr(media_command) + ");" \
            "sys.stderr.buffer.write(b'warning\\n'*4000+b'[h264 @ 0x1] corrupt slice');sys.exit(code)"
        return [str(Path(sys._base_executable)), '-c', code]
    monkeypatch.setattr(module, '_build_ffmpeg_command', command)
    adapter.run()
    values = completed_values(adapter)
    assert values['finalization']['status'] == 'completed'
    assert values['finalization']['input_decode']['status'] == 'degraded'
    assert values['finalization']['input_decode']['diagnostic_count'] > 0
    assert adapter.coordinator.journal.validation(adapter.coordinator.token)['evidence']['report']['passed']


def test_control_objects_are_not_reopened_or_writable_by_path(completing):
    adapter, _, _, _, raw = completing
    adapter.run()
    cap = adapter.capability
    for held in [cap.stage, cap.predecessor]:
        with pytest.raises(OSError):
            held.path.write_bytes(b'foreign replacement')
        with pytest.raises(OSError):
            os.replace(held.path, held.path.with_suffix('.foreign'))
    assert cap.predecessor.read_control() == raw
    assert not adapter.close() and adapter.coordinator.cleanup_evidence()['manifest']['successor_retained']


@pytest.mark.parametrize('capture_status', ['failed', 'interrupted'])
def test_pure_successor_builder_preserves_prior_errors_and_capture_timeline(capture_status):
    from tikrec.manifest_successor_values import successor_bytes
    old = {'schema_version': 1, 'session_id': 'fixture', 'parts_directory': 'parts', 'output_path': 'output',
        'status': capture_status, 'started_at': 10, 'ended_at': 30, 'elapsed_seconds': 20,
        'interrupted': True, 'recovery_performed': True, 'writer_recoveries': [{'evidence': 'original'}],
        'part_count': 2, 'connection_count': 3, 'reconnect_count': 2, 'raw_requested': True,
        'raw_warnings': ['raw_write_failed'], 'error': 'prior [URL redacted]',
        'finalization': {'status': 'pending', 'error': 'prior finalizer evidence'}, 'media': {}}
    report = {'assembly_input_decode': {'status': 'unknown', 'diagnostic_count': 0,
        'diagnostic_codes': [], 'count_capped': False}, 'output_media':
        {'video_codec': 'h264', 'audio_codec': None, 'width': None, 'height': None}}
    values = json.loads(successor_bytes(json.dumps(old).encode(), {'id': 'fixture', 'intent':
        {'parts_path': 'parts', 'output_path': 'output'}}, report))
    for key in old.keys() - {'finalization', 'media'}:
        assert values[key] == old[key]
    assert values['finalization']['error'] == old['finalization']['error']
    assert values['finalization']['input_decode']['status'] == 'unknown'
    assert values['media']['width'] is None


@pytest.mark.parametrize('revoked', [False, True])
def test_historical_completion_or_revoked_live_owner_cannot_write_again(completing, revoked):
    from tikrec.manifest_completion import ManifestCompletion
    adapter, _, _, _, _ = completing
    adapter.run()
    record = adapter.coordinator.journal.manifest_completion(adapter.coordinator.token)
    if revoked:
        adapter.cancel()
    with pytest.raises(Exception):
        ManifestCompletion(adapter.publication)
    with pytest.raises(Exception):
        adapter.capability.complete()
    assert adapter.coordinator.journal.manifest_completion(adapter.coordinator.token) == record


def test_publication_only_defaults_do_not_grant_control_completion(publishing):
    from tikrec.manifest_completion import ManifestCompletion
    adapter, _, _, _ = publishing
    adapter.run()
    assert not adapter.coordinator.manifest_capable
    assert not next(x for x in adapter.coordinator.guard.files if x.path.name == 'session.json').control_right
    with pytest.raises(Exception):
        ManifestCompletion(adapter)
    assert adapter.coordinator.journal.manifest_completion(adapter.coordinator.token) is None


def test_completion_reuses_owned_facts_without_another_probe(completing, monkeypatch):
    import subprocess
    adapter, _, _, _, _ = completing
    def hook(point):
        if point == 'after_publication_result':
            def forbidden(*_, **__):
                raise AssertionError('unowned subprocess during manifest completion')
            monkeypatch.setattr(subprocess, 'run', forbidden)
    adapter.coordinator._fault = hook
    assert adapter.run()['state'] == 'installed'
    assert len(adapter.coordinator.children) == adapter.coordinator.journal.scratch(
        adapter.coordinator.token)['candidate']['sequence'] + 3


def test_replaced_local_successor_owner_cannot_inherit_authority(completing, monkeypatch):
    import copy
    adapter, _, _, _, _ = completing
    def hook(point):
        if point == 'after_manifest_staged_result':
            cap = adapter.coordinator.manifest_owner
            monkeypatch.setattr(cap, 'stage', copy.copy(cap.stage))
    adapter.coordinator._fault = hook
    with pytest.raises(Exception):
        adapter.run()
    assert adapter.capability.stage_owner.handle is not None
    assert len(adapter.coordinator.journal.manifest_completion(adapter.coordinator.token)['steps']) == 1
