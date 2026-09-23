"""A crash-damaged tag can only yield the independently proven prior prefix."""

import hashlib
import json
import os
from dataclasses import replace

import pytest

from tests.test_writer import video
from tests.test_writer_recovery import (crashed_session, evidence_path,
                                        media_bytes, reconciler)
from tikrec.session_parts import _check_structure
from tikrec.writer_recovery import inspect_writer_storage


def bad_trailer(tag):
    """Keep a complete payload while corrupting only its PreviousTagSize."""
    encoded = tag.encoded()
    return encoded[:-4] + b"\0\0\0\0"


def test_bad_trailer_after_valid_media_recovers_only_prior_prefix(tmp_path):
    clean = media_bytes(tmp_path)
    damaged = bad_trailer(video(160, 2)) + b"\0" * 132_390
    store, _, manifest, partial = crashed_session(tmp_path, content=clean + damaged)
    original = partial.read_bytes()
    original_hash = hashlib.sha256(original).hexdigest()

    result = reconciler(store).reconcile()

    recovered = partial.parent / "part-0001.flv"
    evidence = evidence_path(partial.parent)
    assert result.outcome == "resume"
    assert not partial.exists()
    assert recovered.read_bytes() == clean
    _check_structure(recovered)
    assert evidence.read_bytes() == original
    assert hashlib.sha256(evidence.read_bytes()).hexdigest() == original_hash
    record = json.loads(manifest.path.read_text())["writer_recoveries"][0]
    assert record["source_sha256"] == original_hash
    assert record["source_bytes"] == len(original)
    assert record["recovered_bytes"] == len(clean)
    assert record["discarded_trailing_bytes"] == len(damaged)


def test_bad_middle_tag_never_resynchronizes_to_later_tag(tmp_path):
    clean = media_bytes(tmp_path)
    later = video(180, 2).encoded()
    store, _, _, partial = crashed_session(
        tmp_path, content=clean + bad_trailer(video(160, 2)) + later
    )

    assert reconciler(store).reconcile().outcome == "resume"
    assert (partial.parent / "part-0001.flv").read_bytes() == clean
    assert evidence_path(partial.parent).read_bytes().endswith(later)


def test_bad_first_tag_without_media_stays_blocked(tmp_path):
    clean = media_bytes(tmp_path)
    first_size = int.from_bytes(clean[14:17], "big")
    trailer = 13 + 11 + first_size
    content = clean[:trailer] + b"\0\0\0\0" + clean[trailer + 4:]
    store, job, manifest, partial = crashed_session(tmp_path, content=content)

    assert reconciler(store).reconcile().outcome == "failed"
    assert store.load() == job
    assert partial.read_bytes() == content
    assert not evidence_path(partial.parent).exists()
    assert "writer_recoveries" not in manifest.snapshot()


def test_bad_trailer_prefix_rejected_by_media_validator(tmp_path):
    clean = media_bytes(tmp_path)
    store, _, _, partial = crashed_session(
        tmp_path, content=clean + bad_trailer(video(160, 2))
    )
    original = partial.read_bytes()

    result = reconciler(
        store, validator=lambda _: (_ for _ in ()).throw(ValueError("decode failed"))
    ).reconcile()

    assert result.outcome == "failed"
    assert evidence_path(partial.parent).read_bytes() == original
    assert not (partial.parent / "part-0001.flv").exists()
    assert store.load().recovery_reason == "writer_partial_recovery"


@pytest.mark.parametrize("conflict", ["room", "index"])
def test_bad_trailer_does_not_bypass_ownership_or_index(tmp_path, conflict):
    clean = media_bytes(tmp_path)
    store, job, _, partial = crashed_session(
        tmp_path, index=2 if conflict == "index" else 1,
        content=clean + bad_trailer(video(160, 2))
    )
    if conflict == "room":
        store.save(replace(job, room_id="456"))

    assert reconciler(store).reconcile().outcome == "failed"
    assert partial.exists()
    assert not evidence_path(partial.parent).exists()


def test_bad_trailer_recovery_restarts_after_evidence_preservation(tmp_path):
    clean = media_bytes(tmp_path)
    store, job, manifest, partial = crashed_session(
        tmp_path, content=clean + bad_trailer(video(160, 2))
    )
    original = partial.read_bytes()
    plan = inspect_writer_storage(partial.parent, job, manifest.snapshot()).recovery
    store.save(replace(job, state="recovering", recovery_reason="writer_partial_recovery"))
    os.replace(partial, plan.evidence)

    result = reconciler(store).reconcile()

    assert result.outcome == "resume"
    assert plan.evidence.read_bytes() == original
    assert plan.recovered.read_bytes() == clean
    record = json.loads(manifest.path.read_text())["writer_recoveries"][0]
    assert record["discarded_trailing_bytes"] == len(original) - len(clean)
