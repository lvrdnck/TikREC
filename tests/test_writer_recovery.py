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


def crashed_session(tmp_path, *, prior=0, index=None, content=None, state="recording",
                    creator=None):
    output = tmp_path / "out.mp4"
    directory = tmp_path / "out.parts"
    directory.mkdir()
    if prior:
        populate(directory, prior)
    manifest = SessionManifest(directory, output, "tiktok_live", creator=creator, session_id=ID,
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


def test_creator_change_after_initial_inspection_blocks_writer_mutation(tmp_path):
    """The first storage inspection cannot authorize later writer mutation."""
    from tikrec.recovery_session import inspect_recovery_session

    store, _, manifest, partial = crashed_session(tmp_path, creator="creator")
    job_before = store.path.read_bytes()
    partial_before = partial.read_bytes()
    manifest_before = manifest.path.read_bytes()

    def changing_inspector(job, **options):
        result = inspect_recovery_session(job, **options)
        values = json.loads(manifest.path.read_text())
        values["creator"] = "beta"
        manifest.path.write_text(json.dumps(values))
        return result

    result = StartupReconciler(
        store, resolver=no_call, finalizer=no_call, resume_capture=no_call,
        clock=lambda: 2000, media_inspector=lambda _: None,
        writer_validator=lambda _: None, inspector=changing_inspector,
    ).reconcile()
    assert result.outcome == "failed"
    assert store.path.read_bytes() == job_before
    assert partial.read_bytes() == partial_before
    assert not evidence_path(partial.parent).exists()
    assert not (partial.parent / "part-0001.flv").exists()
    assert b'"writer_recoveries"' not in manifest.path.read_bytes()
    assert manifest.path.read_bytes() != manifest_before


@pytest.mark.parametrize("change_kind", ["room", "session", "output", "parts", "partial"])
def test_fresh_writer_preflight_rejects_changed_ownership_without_mutation(
        tmp_path, change_kind):
    """An old initial inspection cannot commit a different current owner or partial."""
    from tikrec.recovery_session import inspect_recovery_session

    store, _, manifest, partial = crashed_session(tmp_path, creator="creator")
    original_job, original_partial = store.path.read_bytes(), partial.read_bytes()

    def changing_inspector(job, **options):
        result = inspect_recovery_session(job, **options)
        if change_kind == "partial":
            changed = bytearray(partial.read_bytes())
            changed[-1] ^= 1
            partial.write_bytes(changed)
        else:
            values = json.loads(manifest.path.read_text())
            key, replacement = {
                "room": ("room_id", "456"),
                "session": ("session_id", "bd9f9372-7cb4-44f2-9a66-2db3e7b831c5"),
                "output": ("output_path", str(tmp_path / "else.mp4")),
                "parts": ("parts_directory", str(tmp_path / "else.parts")),
            }[change_kind]
            values[key] = replacement
            manifest.path.write_text(json.dumps(values))
        return result

    result = StartupReconciler(
        store, resolver=no_call, finalizer=no_call, resume_capture=no_call,
        clock=lambda: 2000, media_inspector=lambda _: None,
        writer_validator=lambda _: None, inspector=changing_inspector,
    ).reconcile()
    assert result.outcome == "failed"
    assert store.path.read_bytes() == original_job
    assert not evidence_path(partial.parent).exists()
    assert not (partial.parent / "part-0001.flv").exists()
    assert partial.exists()
    if change_kind != "partial":
        assert partial.read_bytes() == original_partial
    assert b'"writer_recoveries"' not in manifest.path.read_bytes()


def test_writer_commit_rechecks_manifest_after_media_recovery(tmp_path):
    """A changed owner during repair cannot receive a committed recovery record."""
    store, _, manifest, partial = crashed_session(tmp_path, creator="creator")
    original = partial.read_bytes()

    def changing_validator(_):
        values = json.loads(manifest.path.read_text())
        values["creator"] = "beta"
        manifest.path.write_text(json.dumps(values))

    result = reconciler(store, validator=changing_validator, resolver=no_call).reconcile()
    assert result.outcome == "failed"
    assert evidence_path(partial.parent).read_bytes() == original
    assert not (partial.parent / "part-0001.flv").exists()
    assert b'"writer_recoveries"' not in manifest.path.read_bytes()


def test_job_changed_during_fresh_writer_inspection_blocks_authorization(tmp_path, monkeypatch):
    """A slow read cannot authorize an intent that changed after its first check."""
    import tikrec.writer_recovery_ownership as ownership
    from tikrec.recovery_session import inspect_recovery_session

    store, job, _, _ = crashed_session(tmp_path, creator="creator")
    first = inspect_recovery_session(job, clock=lambda: 2000, media_inspector=lambda _: None)
    token = ownership.capture_writer_ownership(first)

    def changing(current, **options):
        fresh = inspect_recovery_session(current, **options)
        store.save(replace(current, state="reconnecting"))
        return fresh

    monkeypatch.setattr(ownership, "inspect_recovery_session", changing)
    with pytest.raises(ValueError):
        ownership.verify_writer_ownership(token, job, store,
                                          clock=lambda: 2000, media_inspector=lambda _: None)


@pytest.mark.parametrize("phase", ["preserve", "staging", "publish"])
def test_writer_mutation_boundary_rechecks_current_job(tmp_path, monkeypatch, phase):
    """A changed job cannot authorize the next preserve, copy, or publication."""
    import tikrec.reconciliation as reconciliation

    store, job, manifest, partial = crashed_session(tmp_path, creator="creator")
    original = partial.read_bytes()
    verify = reconciliation.verify_writer_phase
    changed = False

    def changing(token, current, durable, source):
        nonlocal changed
        observed = ("preserve" if source == partial else
                    "publish" if (partial.parent / f".tikrec-writer-recovery-{ID}-part-0001.tmp").exists()
                    else "staging")
        if observed == phase and not changed:
            changed = True
            store.save(replace(current, state="reconnecting"))
        return verify(token, current, durable, source)

    monkeypatch.setattr(reconciliation, "verify_writer_phase", changing)
    result = reconciler(store, resolver=no_call).reconcile()
    assert changed and result.outcome == "failed"
    assert not (partial.parent / "part-0001.flv").exists()
    assert (partial if phase == "preserve" else evidence_path(partial.parent)).read_bytes() == original
    assert b'"writer_recoveries"' not in manifest.path.read_bytes()


def test_writer_commit_rechecks_job_after_slow_media_proof(tmp_path, monkeypatch):
    """A job replacement after coherent media proof cannot append."""
    import tikrec.writer_recovery_ownership as ownership

    store, _, manifest, partial = crashed_session(tmp_path, creator="creator")
    original = ownership.prove_recovery_bytes

    def changing(*args):
        result = original(*args)
        store.save(replace(store.load(), state="reconnecting"))
        return result

    monkeypatch.setattr(ownership, "prove_recovery_bytes", changing)
    result = reconciler(store, resolver=no_call).reconcile()
    assert result.outcome == "failed"
    assert (partial.parent / "part-0001.flv").exists()
    assert b'"writer_recoveries"' not in manifest.path.read_bytes()


def test_writer_manifest_commit_is_conditional_on_inspected_bytes(tmp_path):
    """The append cannot overwrite a newer manifest at its write boundary."""
    store, job, manifest, partial = crashed_session(tmp_path, creator="creator")
    from tikrec.recovery_session import inspect_recovery_session
    from tikrec.writer_recovery_evidence import recovery_record
    from tikrec.writer_recovery_ownership import capture_writer_ownership

    session = inspect_recovery_session(job, clock=lambda: 2000, media_inspector=lambda _: None)
    token = capture_writer_ownership(session)
    recover_writer_partial(session.writer_recovery, validator=lambda _: None)
    newer = json.loads(manifest.path.read_text())
    newer["creator"] = "beta"
    manifest.path.write_text(json.dumps(newer))
    with pytest.raises(ValueError):
        manifest.record_writer_recovery(recovery_record(token.plan, 2000),
                                        token.plan.retained.parts,
                                        expected_digest=token.manifest_digest)
    assert json.loads(manifest.path.read_text())["creator"] == "beta"
    assert b'"writer_recoveries"' not in manifest.path.read_bytes()


def test_writer_job_transition_cannot_replace_newer_intent(tmp_path, monkeypatch):
    """A job changed while the replacement is prepared wins over stale recovery."""
    import tikrec.job_state as job_state
    from dataclasses import asdict

    store, job, _, partial = crashed_session(tmp_path, creator="creator")
    dump = job_state.json.dump
    changed = False

    def changing(values, handle, **options):
        nonlocal changed
        if not changed:
            changed = True
            store.path.write_text(json.dumps(asdict(replace(job, state="reconnecting"))))
        return dump(values, handle, **options)

    monkeypatch.setattr(job_state.json, "dump", changing)
    result = reconciler(store, resolver=no_call).reconcile()
    assert changed and result.outcome == "failed"
    assert store.load().state == "reconnecting"
    assert partial.exists() and not evidence_path(partial.parent).exists()


def test_writer_manifest_promotion_rechecks_job_after_serialization(tmp_path, monkeypatch):
    """The final manifest replace cannot use job ownership checked before JSON I/O."""
    import tikrec.manifest_io as manifest_io
    from dataclasses import asdict

    store, _, manifest, partial = crashed_session(tmp_path, creator="creator")
    dump = manifest_io.json.dump
    changed = False

    def changing(values, handle, **options):
        nonlocal changed
        if values.get("writer_recoveries") and not changed:
            changed = True
            store.path.write_text(json.dumps(asdict(replace(store.load(),
                                                             state="reconnecting"))))
        return dump(values, handle, **options)

    monkeypatch.setattr(manifest_io.json, "dump", changing)
    result = reconciler(store, resolver=no_call).reconcile()
    assert changed and result.outcome == "failed"
    assert (partial.parent / "part-0001.flv").exists()
    assert b'"writer_recoveries"' not in manifest.path.read_bytes()


def test_final_manifest_guard_rejects_equal_eof_after_earlier_checks(
        tmp_path, monkeypatch):
    """A false prefix proof cannot publish recovery after the temp write."""
    import tikrec.writer_recovery_ownership as ownership

    store, _, manifest, partial = crashed_session(tmp_path, creator="creator")
    committed = manifest.path.read_bytes()
    temporary = manifest.path.with_name(f".{manifest.path.name}.partial")
    original = ownership.prove_recovery_bytes
    changed = False
    inventory_at_guard = None

    def shorten_during_final_proof(left, right, source_bytes, recovered_bytes, digest):
        nonlocal changed, inventory_at_guard
        if temporary.exists() and not changed:
            changed = True
            inventory_at_guard = {path.name for path in partial.parent.iterdir()}
            left.write_bytes(b"")
            right.write_bytes(b"")
        return original(left, right, source_bytes, recovered_bytes, digest)

    monkeypatch.setattr(ownership, "prove_recovery_bytes", shorten_during_final_proof)
    result = reconciler(store, resolver=no_call).reconcile()
    assert changed and result.outcome == "failed"
    assert manifest.path.read_bytes() == committed
    assert b'"writer_recoveries"' not in manifest.path.read_bytes()
    assert inventory_at_guard - {temporary.name} == {
        path.name for path in partial.parent.iterdir()}
    assert not temporary.exists()
    assert evidence_path(partial.parent).exists()
    assert (partial.parent / "part-0001.flv").exists()
