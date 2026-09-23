"""Crash-during-FFmpeg recovery preserves evidence before settling service intent."""

import json

from pathlib import Path

import pytest

from tests.test_reconciliation import keep_finalizer, no_call, saved_session
from tikrec.finalization_recovery import preserved_partial_path
from tikrec.finalize import _temporary_output_path
from tikrec.reconciliation import StartupReconciler


def crashed_finalization(tmp_path, content=b"encoder partial"):
    """Build the durable/manifest state that exists while FFmpeg is running."""
    store, job, manifest = saved_session(tmp_path, state="finalizing")
    manifest.mark_finalizing(tuple((tmp_path / "out.parts").glob("*.flv")))
    temporary = _temporary_output_path(Path(job.output_path))
    temporary.write_bytes(content)
    return store, job, manifest, temporary


def recovery(store, *, finalizer=no_call):
    return StartupReconciler(
        store, resolver=no_call, finalizer=finalizer, clock=lambda: 2000,
        media_inspector=lambda _: None,
    )


def test_probeable_encoder_partial_is_preserved_and_refinalized(tmp_path):
    store, job, manifest, temporary = crashed_finalization(tmp_path, b"complete output")

    result = recovery(store, finalizer=keep_finalizer).reconcile()

    output = Path(job.output_path)
    evidence = preserved_partial_path(output, job.session_id)
    assert result.outcome == "settled" and result.reason == "recovery_finalization"
    assert output.read_bytes() == b"final" and not temporary.exists()
    assert evidence.read_bytes() == b"complete output"
    assert store.load().state == "completed" and store.load().finalization_completed
    facts = json.loads(manifest.path.read_text())
    assert facts["finalization"] == {
        "status": "completed", "error": None,
        "input_decode": {"status": "unknown", "diagnostic_count": 0,
                         "diagnostic_codes": [], "count_capped": False},
    }
    assert facts["recovery_performed"] and facts["interrupted"]


def test_unreadable_encoder_partial_is_preserved_then_refinalized(tmp_path):
    store, job, _, temporary = crashed_finalization(tmp_path, b"missing moov")

    result = recovery(store, finalizer=keep_finalizer).reconcile()

    output = Path(job.output_path)
    evidence = preserved_partial_path(output, job.session_id)
    assert result.outcome == "settled" and output.read_bytes() == b"final"
    assert evidence.read_bytes() == b"missing moov" and not temporary.exists()


def test_failed_refinalization_retains_evidence_and_can_retry(tmp_path):
    store, job, _, temporary = crashed_finalization(tmp_path, b"incomplete output")
    output = Path(job.output_path)
    evidence = preserved_partial_path(output, job.session_id)

    def fail(parts, requested_output):
        assert evidence.read_bytes() == b"incomplete output"
        assert tuple(parts) and requested_output == output
        raise OSError("encoder unavailable")

    first = recovery(store, finalizer=fail).reconcile()

    assert first.outcome == "failed" and store.load().state == "finalizing"
    assert evidence.read_bytes() == b"incomplete output" and not temporary.exists()
    assert not output.exists()

    second = recovery(store, finalizer=keep_finalizer).reconcile()

    assert second.outcome == "settled" and output.read_bytes() == b"final"
    assert evidence.read_bytes() == b"incomplete output"


def test_preserved_partial_collision_blocks_without_changes(tmp_path):
    store, job, manifest, temporary = crashed_finalization(tmp_path)
    evidence = preserved_partial_path(Path(job.output_path), job.session_id)
    evidence.write_bytes(b"older evidence")
    before = {
        path: path.read_bytes()
        for path in (store.path, manifest.path, temporary, evidence)
    }

    result = recovery(store, finalizer=no_call).reconcile()

    assert result.outcome == "failed" and result.blocked
    assert all(path.read_bytes() == content for path, content in before.items())


@pytest.mark.parametrize("kind", ["empty", "directory"])
def test_invalid_encoder_partial_blocks_without_mutation(tmp_path, kind):
    store, job, manifest = saved_session(tmp_path, state="finalizing")
    manifest.mark_finalizing(tuple((tmp_path / "out.parts").glob("*.flv")))
    temporary = _temporary_output_path(Path(job.output_path))
    if kind == "empty":
        temporary.touch()
    else:
        temporary.mkdir()
    before_job, before_manifest = store.path.read_bytes(), manifest.path.read_bytes()

    result = recovery(store, finalizer=no_call).reconcile()

    assert result.outcome == "failed" and result.blocked
    assert store.path.read_bytes() == before_job and manifest.path.read_bytes() == before_manifest
    assert temporary.exists()


def test_output_and_partial_together_remain_ambiguous(tmp_path):
    store, job, manifest, temporary = crashed_finalization(tmp_path)
    output = Path(job.output_path)
    output.write_bytes(b"existing output")
    before_job, before_manifest = store.path.read_bytes(), manifest.path.read_bytes()

    result = recovery(store, finalizer=no_call).reconcile()

    assert result.outcome == "failed" and result.reason == "existing_output"
    assert output.read_bytes() == b"existing output" and temporary.read_bytes() == b"encoder partial"
    assert store.path.read_bytes() == before_job and manifest.path.read_bytes() == before_manifest
