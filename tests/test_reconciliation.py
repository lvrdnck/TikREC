"""Offline service restart decisions with real retained FLV/session storage."""

import json
from dataclasses import replace

import pytest

from tests.test_session_parts import populate
from tests.test_session_resume import ID, update
from tikrec.capture import CaptureResult
from tikrec.job_state import JobState, JobStateStore
from tikrec.manifest import SessionManifest
from tikrec.media import MediaInfo
from tikrec.reconciliation import DeferredReconciliationResult, StartupReconciler
from tikrec.tiktok import (LiveResolution, TikTokOfflineError, TikTokResolutionError,
                          TikTokResolutionTransientError)


PAGE = "https://www.tiktok.com/@creator/live"
SIGNED = "https://cdn.test/live.flv?signature=secret"


def saved_session(tmp_path, **changes):
    output = tmp_path / "out.mp4"
    directory = tmp_path / "out.parts"
    directory.mkdir()
    populate(directory)
    manifest = SessionManifest(directory, output, "tiktok_live", session_id=ID,
                               clock=lambda: 1000, media_inspector=lambda _: None)
    manifest.start(connection_count=2)
    manifest.update_capture(tuple(directory.glob("*.flv")))
    manifest.record_room_identity("123")
    job = JobState(ID, PAGE, str(output), str(directory), 1000, state="recording", room_id="123")
    job = replace(job, **changes)
    store = JobStateStore(tmp_path / "job.json")
    store.save(job)
    return store, job, manifest


def no_call(*args, **kwargs):
    pytest.fail("unexpected resolver/capture/finalizer call")


def reconciler(store, **options):
    return StartupReconciler(store, clock=lambda: 2000, media_inspector=lambda _: None, **options)


def keep_finalizer(parts, output):
    assert [p.name for p in parts] == ["part-0001.flv", "part-0002.flv"]
    assert not output.exists()
    output.write_bytes(b"final")
    return output


def test_absent_intent_is_idle(tmp_path):
    result = reconciler(JobStateStore(tmp_path / "job.json"), resolver=no_call).reconcile()
    assert result.outcome == "idle" and result.job is None


@pytest.mark.parametrize("changes", [
    {"state": "completed", "ended_at": 1100},
    {"state": "failed", "ended_at": 1100},
    {"finalization_completed": True},
    {"state": "completed", "ended_at": 1100, "stop_requested": True},
])
def test_terminal_intent_never_relaunches(tmp_path, changes):
    store, job, _ = saved_session(tmp_path, **changes)
    before = store.path.read_bytes()
    result = reconciler(store, resolver=no_call, finalizer=no_call).reconcile()
    assert result.outcome == "settled" and result.job == job
    assert store.path.read_bytes() == before


def test_same_room_commits_resume_before_capture_and_preserves_identity(tmp_path):
    store, job, _ = saved_session(tmp_path)
    observed, calls = [], []
    def resume(url, **options):
        durable = store.load()
        assert durable.state == "resuming" and durable.resume_count == 1
        calls.append((url, options))
        return CaptureResult((), None)
    recovery = reconciler(store, resolver=lambda _: LiveResolution("00123", SIGNED), resume_capture=resume)
    result = recovery.reconcile(observe=observed.append)
    assert [j.state for j in observed] == ["reconciling", "resuming"]
    assert result.outcome == "resume" and result.job.session_id == job.session_id
    assert result.job.room_id == "123" and result.job.resume_count == 1
    recovery.resume(result)
    assert calls[0][0] == PAGE
    assert str(calls[0][1]["parts_directory"]) == job.parts_directory
    assert calls[0][1]["session_id"] == ID
    assert "secret" not in store.path.read_text() and SIGNED not in repr(result)
    records = [json.loads(line) for line in (tmp_path / "out.parts/connections.jsonl").read_text().splitlines()]
    assert records[-1]["reason"] == "process_restart" and records[-1]["resume_count"] == 1


@pytest.mark.parametrize("kind", ["offline", "different", "stopped", "finalizing"])
def test_end_stop_and_finalizing_safely_finalize_prior_parts(tmp_path, kind):
    changes = {"stop_requested": True} if kind == "stopped" else {}
    if kind == "finalizing":
        changes["state"] = "finalizing"
    store, job, manifest = saved_session(tmp_path, **changes)
    old = {p.name: p.read_bytes() for p in (tmp_path / "out.parts").glob("*.flv")}
    def resolve(page):
        assert page == PAGE
        if kind in {"stopped", "finalizing"}:
            no_call()
        if kind == "offline":
            raise TikTokOfflineError("offline", status=4, room_id="123")
        return LiveResolution("456", SIGNED)
    result = reconciler(store, resolver=resolve, finalizer=keep_finalizer, resume_capture=no_call).reconcile()
    assert result.outcome == "settled" and result.job.finalization_completed
    assert result.reason == {"offline": "room_ended", "different": "live_changed",
                             "stopped": "user_stop", "finalizing": "recovery_finalization"}[kind]
    assert result.job.room_id == "123" and result.job.resume_count == 0
    assert old == {p.name: p.read_bytes() for p in (tmp_path / "out.parts").glob("*.flv")}
    facts = json.loads(manifest.path.read_text())
    assert facts["finalization"]["status"] == "completed" and facts["recovery_performed"]
    assert facts["started_at"] == 1000 and facts["ended_at"] == 2000


@pytest.mark.parametrize("message", ["DNS failure", "timeout", "HTTP 503", "endpoint unavailable"])
def test_transient_resolution_is_deferred_and_intent_unchanged(tmp_path, message):
    store, job, manifest = saved_session(tmp_path)
    before, evidence = store.path.read_bytes(), manifest.path.read_bytes()
    calls = []
    def resolve(page):
        calls.append(page)
        raise TikTokResolutionTransientError(message + " " + SIGNED)
    result = reconciler(store, resolver=resolve, finalizer=no_call, resume_capture=no_call).reconcile()
    assert result.outcome == "deferred" and result.blocked
    assert isinstance(result, DeferredReconciliationResult)
    assert result.reason == "identity_unavailable" and result.job == job
    assert store.path.read_bytes() == before and manifest.path.read_bytes() == evidence
    assert calls == [PAGE] and not (tmp_path / "out.mp4").exists()
    assert "secret" not in repr(result)


@pytest.mark.parametrize("error", [TikTokResolutionError(SIGNED), ValueError(SIGNED), RuntimeError(SIGNED)])
def test_malformed_or_programming_error_is_failed_not_offline(tmp_path, error):
    store, _, manifest = saved_session(tmp_path)
    before = manifest.path.read_bytes()
    def resolve(page):
        raise error
    result = reconciler(store, resolver=resolve, finalizer=no_call).reconcile()
    assert result.outcome == "failed" and result.reason == "ambiguous_state"
    assert manifest.path.read_bytes() == before and "secret" not in repr(result)


def test_legacy_string_resolution_cannot_resume(tmp_path):
    store, _, _ = saved_session(tmp_path)
    result = reconciler(store, resolver=lambda _: SIGNED, finalizer=no_call).reconcile()
    assert result.outcome == "failed" and result.blocked


@pytest.mark.parametrize("changes", [
    {"session_id": "bd9f9372-7cb4-44f2-9a66-2db3e7b831c5"},
    {"room_id": "456"}, {"room_id": None}, {"source_type": "direct_flv"},
    {"parts_directory": "other.parts"}, {"output_path": "other.mp4"},
    {"part_count": 99}, {"finalization": {"status": "running"}},
])
def test_conflicting_session_never_resolves_or_writes(tmp_path, changes):
    store, _, manifest = saved_session(tmp_path)
    update(tmp_path / "out.parts", **changes)
    before = {p.name: p.read_bytes() for p in (tmp_path / "out.parts").iterdir()}
    result = reconciler(store, resolver=no_call, finalizer=no_call).reconcile()
    assert result.outcome == "failed"
    assert before == {p.name: p.read_bytes() for p in manifest.path.parent.iterdir()}


def test_missing_saved_identity_cannot_resume(tmp_path):
    store, _, _ = saved_session(tmp_path, room_id=None)
    assert reconciler(store, resolver=no_call).reconcile().outcome == "failed"


@pytest.mark.parametrize("artifact", [".part-0003.flv.partial", ".out.partial.mp4", "out.mp4"])
def test_partial_or_ambiguous_output_is_preserved(tmp_path, artifact):
    store, _, _ = saved_session(tmp_path)
    path = (tmp_path / "out.parts" if artifact.startswith(".part") else tmp_path) / artifact
    path.write_bytes(b"keep")
    result = reconciler(store, resolver=no_call, finalizer=no_call).reconcile()
    assert result.outcome == "failed" and path.read_bytes() == b"keep"


def test_completed_manifest_plus_matching_output_settles_without_overwrite(tmp_path):
    store, _, manifest = saved_session(tmp_path, state="finalizing")
    output = tmp_path / "out.mp4"
    output.write_bytes(b"keep")
    manifest.complete(tuple((tmp_path / "out.parts").glob("*.flv")), output_path=output,
                      finalization_status="completed")
    recovery = StartupReconciler(store, resolver=no_call, finalizer=no_call, clock=lambda: 2000,
        media_inspector=lambda _: MediaInfo(video_codec="h264", format_name="mp4", duration_seconds=1))
    result = recovery.reconcile()
    assert result.outcome == "settled" and result.reason == "existing_output"
    assert store.load().finalization_completed and output.read_bytes() == b"keep"


def test_finalizer_failure_keeps_nonterminal_intent_and_parts(tmp_path):
    store, _, _ = saved_session(tmp_path, stop_requested=True)
    def fail(parts, output):
        raise RuntimeError(SIGNED)
    result = reconciler(store, resolver=no_call, finalizer=fail).reconcile()
    assert result.outcome == "failed" and store.load().state == "finalizing"
    assert not store.load().finalization_completed
    assert len(list((tmp_path / "out.parts").glob("*.flv"))) == 2


@pytest.mark.parametrize("document", ["{", "{}", '{"stop_requested":false,"stop_requested":true}'])
def test_corrupt_job_is_preserved_and_failed(tmp_path, document):
    store = JobStateStore(tmp_path / "job.json")
    store.path.write_text(document)
    result = reconciler(store, resolver=no_call, finalizer=no_call).reconcile()
    assert result.outcome == "failed" and result.job is None and result.blocked
    assert store.path.read_text() == document


def test_failed_durable_resume_commit_prevents_media_start(tmp_path):
    _, job, _ = saved_session(tmp_path)
    class FailingStore:
        def load(self):
            return job
        def save(self, updated):
            assert updated.state == "resuming"
            raise OSError("disk unavailable " + SIGNED)
    recovery = reconciler(FailingStore(), resolver=lambda _: LiveResolution("123", SIGNED),
                          resume_capture=no_call)
    result = recovery.reconcile()
    assert result.outcome == "failed" and result.blocked and "secret" not in repr(result)


@pytest.mark.parametrize("transport", [None, "file:///tmp/live.flv", "https://cdn.test/live.m3u8"])
def test_malformed_structured_transport_never_resumes(tmp_path, transport):
    store, job, _ = saved_session(tmp_path)
    result = reconciler(store, resolver=lambda _: LiveResolution("123", transport),
                        resume_capture=no_call, finalizer=no_call).reconcile()
    assert result.outcome == "failed" and store.load() == job
