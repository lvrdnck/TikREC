"""Native Windows recovery must admit aged, unchanged writer evidence."""

from dataclasses import replace
import hashlib
import json
import os
import time

import pytest

from tests.test_writer_recovery import crashed_session, evidence_path, reconciler
from tikrec.writer_recovery import inspect_writer_storage, recover_writer_partial


@pytest.mark.skipif(os.name != "nt", reason="native Windows path/handle metadata")
@pytest.mark.parametrize("state", ["fresh", "published"])
def test_aged_writer_partial_commits_recovery_on_windows(tmp_path, state):
    """Fresh recovery and published retry must tolerate native ctime disagreement."""
    store, job, manifest, partial = crashed_session(tmp_path)
    original = partial.read_bytes()
    evidence = evidence_path(partial.parent)
    part = partial.parent / "part-0001.flv"
    # Aging makes the native ctime disagreement observable on affected runtimes.
    time.sleep(1.1)
    if state == "published":
        plan = inspect_writer_storage(partial.parent, job, manifest.snapshot()).recovery
        store.save(replace(job, state="recovering", recovery_reason="writer_partial_recovery"))
        recover_writer_partial(plan, validator=lambda _: None)
        assert not partial.exists() and evidence.exists() and part.exists()
        assert json.loads(manifest.path.read_text())["part_count"] == 0
        assert "writer_recoveries" not in json.loads(manifest.path.read_text())

    disagreements = []

    def observe_native_metadata(_):
        with evidence.open("rb") as handle:
            path_details, handle_details = evidence.lstat(), os.fstat(handle.fileno())
        disagreements.append(path_details.st_ctime_ns != handle_details.st_ctime_ns)
        for field in ("st_mode", "st_size", "st_dev", "st_ino", "st_mtime_ns",
                      "st_nlink", "st_file_attributes"):
            assert getattr(path_details, field) == getattr(handle_details, field)

    result = reconciler(store, validator=observe_native_metadata).reconcile()

    # This is real lstat/fstat evidence, with no injected identity normalization.
    assert len(disagreements) == 1
    assert result.outcome == "resume" and result.reason == "process_restart", disagreements
    assert store.load().state == "resuming" and store.load().resume_count == 1
    assert not partial.exists()
    assert evidence.read_bytes() == part.read_bytes() == original
    facts = json.loads(manifest.path.read_text())
    assert facts["part_count"] == 1 and facts["recovery_performed"] is True
    assert len(facts["writer_recoveries"]) == 1
    record = facts["writer_recoveries"][0]
    assert record["source_sha256"] == hashlib.sha256(original).hexdigest()
    assert record["source_bytes"] == record["recovered_bytes"] == len(original)
    assert record["discarded_trailing_bytes"] == 0
    # A later startup must validate the persisted record without duplicating it.
    assert reconciler(store).reconcile().outcome == "resume"
    assert json.loads(manifest.path.read_text())["writer_recoveries"] == [record]
