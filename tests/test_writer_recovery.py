"""Crash-writer recovery preserves source bytes and admits only proven media."""

import json
import hashlib
import os
from dataclasses import replace
from pathlib import Path

import pytest

from tests.test_reconciliation import PAGE, SIGNED, no_call
from tests.test_session_parts import populate
from tests.test_session_resume import ID, update
from tests.test_writer import audio, audio_configuration, avc_configuration, video
from tikrec.capture_resume import capture_tags_resume
from tikrec.job_state import JobState, JobStateStore
from tikrec.manifest import SessionManifest
from tikrec.reconciliation import StartupReconciler
from tikrec.session_resume import begin_resume, prepare_resume
from tikrec.tiktok import LiveResolution
from tikrec.writer import write_parts
from tikrec.writer_recovery import inspect_writer_storage, recover_writer_partial


def media_bytes(tmp_path):
    fixture = tmp_path / "fixture"
    part = write_parts([
        audio_configuration(90), avc_configuration(100, b"config"),
        video(120, 1), audio(125), video(140, 2),
    ], fixture)[0]
    return part.read_bytes()


def crashed_session(tmp_path, *, prior=0, index=None, content=None, state="recording"):
    output = tmp_path / "out.mp4"
    directory = tmp_path / "out.parts"
    directory.mkdir()
    if prior:
        populate(directory, prior)
    manifest = SessionManifest(directory, output, "tiktok_live", session_id=ID,
                               clock=lambda: 1000, media_inspector=lambda _: None)
    manifest.start(connection_count=1)
    manifest.update_capture(tuple(directory.glob("part-*.flv")), connection_count=1)
    manifest.record_room_identity("123")
    job = JobState(ID, PAGE, str(output), str(directory), 1000,
                   state=state, room_id="123")
    store = JobStateStore(tmp_path / "job.json")
    store.save(job)
    index = prior + 1 if index is None else index
    partial = directory / f".part-{index:04d}.flv.partial"
    partial.write_bytes(media_bytes(tmp_path) if content is None else content)
    return store, job, manifest, partial


def reconciler(store, *, validator=lambda _: None, resolver=None):
    return StartupReconciler(
        store,
        resolver=resolver or (lambda _: LiveResolution("123", SIGNED)),
        finalizer=no_call,
        resume_capture=no_call,
        clock=lambda: 2000,
        media_inspector=lambda _: None,
        writer_validator=validator,
    )


def evidence_path(directory, index=1):
    return directory / f".tikrec-writer-crash-{ID}-part-{index:04d}.evidence"


def test_clean_owned_partial_is_preserved_admitted_and_continues_at_next_part(tmp_path):
    store, _, manifest, partial = crashed_session(tmp_path)
    original = partial.read_bytes()

    result = reconciler(store).reconcile()

    directory = partial.parent
    evidence = evidence_path(directory)
    recovered = directory / "part-0001.flv"
    assert result.outcome == "resume" and store.load().state == "resuming"
    assert not partial.exists() and evidence.read_bytes() == original
    assert recovered.read_bytes() == original
    facts = json.loads(manifest.path.read_text())
    assert facts["started_at"] == 1000 and facts["ended_at"] is None
    assert facts["part_count"] == 1 and facts["connection_count"] == 1
    assert facts["writer_recoveries"] == [{
        "timestamp": 2000,
        "part": "part-0001.flv",
        "evidence": evidence.name,
        "source_sha256": hashlib.sha256(original).hexdigest(),
        "source_bytes": len(original),
        "recovered_bytes": len(original),
        "discarded_trailing_bytes": 0,
    }]
    prepared = prepare_resume(directory, output_path=tmp_path / "out.mp4",
                              session_id=ID, source_type="tiktok_live",
                              media_inspector=lambda _: None)
    assert prepared.retained.next_index == 2 and prepared.next_connection == 2

    capture_tags_resume([
        audio_configuration(200), avc_configuration(210, b"next"),
        video(220, 1), audio(225),
    ], parts_directory=directory, session_id=ID, source_type="tiktok_live",
       media_inspector=lambda _: None)
    assert (directory / "part-0002.flv").is_file()
    assert evidence.read_bytes() == original and recovered.read_bytes() == original


def test_trailing_torn_tag_preserves_original_and_recovers_only_safe_prefix(tmp_path):
    clean = media_bytes(tmp_path)
    torn = video(160, 2).encoded()[:-3]
    store, _, manifest, partial = crashed_session(tmp_path, content=clean + torn)
    original = partial.read_bytes()

    result = reconciler(store).reconcile()

    evidence = evidence_path(partial.parent)
    assert result.outcome == "resume"
    assert evidence.read_bytes() == original
    assert (partial.parent / "part-0001.flv").read_bytes() == clean
    record = json.loads(manifest.path.read_text())["writer_recoveries"][0]
    assert record["recovered_bytes"] == len(clean)
    assert record["discarded_trailing_bytes"] == len(torn)


@pytest.mark.parametrize("kind", ["zero", "malformed"])
def test_empty_or_malformed_partial_blocks_without_mutation(tmp_path, kind):
    clean = media_bytes(tmp_path)
    first_trailer = 24 + int.from_bytes(clean[14:17], "big")
    content = b"" if kind == "zero" else clean[:first_trailer] + b"\0" * 4 + clean[first_trailer + 4:]
    store, job, manifest, partial = crashed_session(tmp_path, content=content)
    before = store.path.read_bytes(), manifest.path.read_bytes(), partial.read_bytes()

    result = reconciler(store, resolver=no_call).reconcile()

    assert result.outcome == "failed" and result.blocked
    assert (store.path.read_bytes(), manifest.path.read_bytes(), partial.read_bytes()) == before


@pytest.mark.parametrize("case", ["unowned", "wrong_index", "same_index", "multiple"])
def test_ambiguous_partial_inventory_blocks_and_preserves_everything(tmp_path, case):
    prior = 1 if case == "same_index" else 0
    index = 1 if case != "wrong_index" else 2
    state = "reconnecting" if case == "unowned" else "recording"
    store, _, manifest, partial = crashed_session(
        tmp_path, prior=prior, index=index, state=state
    )
    if case == "multiple":
        (partial.parent / ".part-0002.flv.partial").write_bytes(partial.read_bytes())
    before = {path.name: path.read_bytes() for path in partial.parent.iterdir() if path.is_file()}

    result = reconciler(store, resolver=no_call).reconcile()

    assert result.outcome == "failed" and result.blocked
    assert before == {path.name: path.read_bytes()
                      for path in manifest.path.parent.iterdir() if path.is_file()}


def test_evidence_name_collision_blocks_without_moving_partial(tmp_path):
    store, _, manifest, partial = crashed_session(tmp_path)
    evidence = evidence_path(partial.parent)
    evidence.write_bytes(b"older evidence")
    before = store.path.read_bytes(), manifest.path.read_bytes(), partial.read_bytes(), evidence.read_bytes()

    result = reconciler(store, resolver=no_call).reconcile()

    assert result.outcome == "failed"
    assert (store.path.read_bytes(), manifest.path.read_bytes(),
            partial.read_bytes(), evidence.read_bytes()) == before


@pytest.mark.parametrize("kind", ["directory", "symlink"])
def test_nonregular_or_symlink_partial_blocks(tmp_path, monkeypatch, kind):
    store, _, manifest, partial = crashed_session(tmp_path)
    original = partial.read_bytes()
    if kind == "directory":
        partial.unlink()
        partial.mkdir()
    else:
        is_symlink = Path.is_symlink
        monkeypatch.setattr(Path, "is_symlink",
                            lambda path: path == partial or is_symlink(path))

    result = reconciler(store, resolver=no_call).reconcile()

    assert result.outcome == "failed" and manifest.path.is_file()
    if kind == "directory":
        assert partial.is_dir()
    else:
        assert partial.read_bytes() == original


@pytest.mark.parametrize("conflict", ["session", "room", "path", "finalization", "output"])
def test_identity_path_or_lifecycle_conflict_blocks_before_preservation(tmp_path, conflict):
    store, _, manifest, partial = crashed_session(tmp_path)
    if conflict == "session":
        update(partial.parent, session_id="bd9f9372-7cb4-44f2-9a66-2db3e7b831c5")
    elif conflict == "room":
        update(partial.parent, room_id="456")
    elif conflict == "path":
        update(partial.parent, parts_directory=str(tmp_path / "other.parts"))
    elif conflict == "finalization":
        update(partial.parent, finalization={"status": "running", "error": None})
    else:
        (tmp_path / "out.mp4").write_bytes(b"existing")
    original = partial.read_bytes()

    result = reconciler(store, resolver=no_call).reconcile()

    assert result.outcome == "failed" and partial.read_bytes() == original
    assert not evidence_path(partial.parent).exists()


def test_media_validation_failure_keeps_exact_preserved_source_and_no_part(tmp_path):
    store, _, _, partial = crashed_session(tmp_path)
    original = partial.read_bytes()

    result = reconciler(
        store, validator=lambda _: (_ for _ in ()).throw(ValueError("decode failed")),
        resolver=no_call,
    ).reconcile()

    assert result.outcome == "failed" and result.blocked
    assert not partial.exists() and evidence_path(partial.parent).read_bytes() == original
    assert not (partial.parent / "part-0001.flv").exists()
    assert store.load().state == "recovering"
    assert store.load().recovery_reason == "writer_partial_recovery"


def test_same_size_source_change_after_inspection_blocks_before_move(tmp_path):
    store, job, manifest, partial = crashed_session(tmp_path)
    inspection = inspect_writer_storage(partial.parent, job, manifest.snapshot())
    changed = bytearray(partial.read_bytes())
    changed[-1] ^= 1
    partial.write_bytes(changed)
    store.save(replace(job, state="recovering", recovery_reason="writer_partial_recovery"))

    with pytest.raises(ValueError, match="changed"):
        recover_writer_partial(inspection.recovery, validator=lambda _: None)

    assert partial.read_bytes() == changed
    assert not inspection.recovery.evidence.exists()


def test_restart_after_evidence_preservation_completes_same_recovery(tmp_path):
    store, job, manifest, partial = crashed_session(tmp_path)
    original = partial.read_bytes()
    inspection = inspect_writer_storage(partial.parent, job, manifest.snapshot())
    store.save(replace(job, state="recovering", recovery_reason="writer_partial_recovery"))
    os.replace(partial, inspection.recovery.evidence)

    result = reconciler(store).reconcile()

    assert result.outcome == "resume"
    assert inspection.recovery.evidence.read_bytes() == original
    assert inspection.recovery.recovered.read_bytes() == original


def test_restart_after_part_publication_commits_missing_manifest_evidence(tmp_path):
    store, job, manifest, partial = crashed_session(tmp_path)
    original = partial.read_bytes()
    inspection = inspect_writer_storage(partial.parent, job, manifest.snapshot())
    store.save(replace(job, state="recovering", recovery_reason="writer_partial_recovery"))
    os.replace(partial, inspection.recovery.evidence)
    recover_writer_partial(inspection.recovery, validator=lambda _: None)
    assert "writer_recoveries" not in manifest.snapshot()

    result = reconciler(store).reconcile()

    assert result.outcome == "resume"
    facts = json.loads(manifest.path.read_text())
    assert facts["writer_recoveries"][0]["source_bytes"] == len(original)
    assert inspection.recovery.evidence.read_bytes() == original
    assert inspection.recovery.recovered.read_bytes() == original


def test_later_crash_recovers_next_part_without_conflicting_prior_evidence(tmp_path):
    store, _, manifest, partial = crashed_session(tmp_path)
    first = reconciler(store).reconcile()
    assert first.outcome == "resume"
    session = prepare_resume(partial.parent, output_path=tmp_path / "out.mp4",
                             session_id=ID, source_type="tiktok_live",
                             media_inspector=lambda _: None)
    begin_resume(session, output_path=tmp_path / "out.mp4", clock=lambda: 1500)
    store.save(replace(store.load(), state="recording", recovery_reason=None))
    second_partial = partial.parent / ".part-0002.flv.partial"
    second_partial.write_bytes(evidence_path(partial.parent).read_bytes())

    second = reconciler(store).reconcile()

    assert second.outcome == "resume" and second.job.resume_count == 2
    facts = json.loads(manifest.path.read_text())
    assert [record["part"] for record in facts["writer_recoveries"]] == [
        "part-0001.flv", "part-0002.flv",
    ]
    prepared = prepare_resume(partial.parent, output_path=tmp_path / "out.mp4",
                              session_id=ID, source_type="tiktok_live",
                              media_inspector=lambda _: None)
    assert prepared.retained.next_index == 3 and prepared.next_connection == 3
