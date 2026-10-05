"""Complete inventory checks bracket artifact binding, hashing and final seal hooks."""

import os

import pytest

from tests.attempt_scratch_helpers import scratch_runner, write_candidate, sealed, managed_process
from tikrec.attempt_coordinator import AttemptError


pytestmark = pytest.mark.skipif(os.name != "nt", reason="actual Windows scratch objects")


@pytest.mark.parametrize("boundary", ["after_scratch_create", "after_scratch_bind"])
def test_workspace_binding_hooks_preserve_unexplained_entry_as_held(scratch_runner, boundary):
    runner = scratch_runner
    def fault(point):
        if point == boundary:
            (runner.scratch.path / "unexpected.txt").write_bytes(b"unexpected")
    runner._fault = fault
    with pytest.raises(AttemptError):
        runner.reserve_scratch()
    assert runner.journal.scratch(runner.token)["state"] == "held"
    assert (runner.scratch.path / "unexpected.txt").read_bytes() == b"unexpected"
    assert not runner.children and not runner.close()


@pytest.mark.parametrize("boundary", ["after_candidate_created", "after_artifact_bind", "before_candidate_ready"])
def test_added_entry_at_unlocked_sealing_boundary_is_held(scratch_runner, boundary):
    runner = scratch_runner
    scratch, launch = write_candidate(runner, helpers=("z.txt", "a.txt"))
    def fault(point):
        if point == boundary:
            (scratch.path / "unexpected.txt").write_bytes(b"preserve unexpected")
    runner._fault = fault
    with pytest.raises(Exception, match="inventory changed"):
        scratch.seal_candidate(launch)
    assert runner.journal.scratch(runner.token)["candidate"] is None
    assert runner.journal.scratch(runner.token)["state"] == "held"
    assert (scratch.path / "unexpected.txt").exists()
    assert set(scratch.artifacts) == {"a.txt", "candidate.mp4", "z.txt"}
    assert not runner.close()


@pytest.mark.parametrize("change", ["append", "missing", "replacement"])
def test_exact_helper_evidence_is_rechecked_after_first_observation(scratch_runner, change):
    runner = scratch_runner
    scratch, launch = write_candidate(runner, helpers=("z.txt", "a.txt"))
    def fault(point):
        if point != "after_artifact_bind":
            return
        held = scratch.artifacts["z.txt"]
        if change == "append":
            # Mutate through the disposable owner's exact descriptor; normal
            # external opens are already denied by the production share mask.
            os.lseek(held.fd, 0, os.SEEK_END)
            os.write(held.fd, b"changed")
            os.fsync(held.fd)
        else:
            held.close()
            (scratch.path / "z.txt").unlink()
            if change == "replacement":
                (scratch.path / "z.txt").write_bytes(b"replacement")
    runner._fault = fault
    with pytest.raises(Exception):
        scratch.seal_candidate(launch)
    assert runner.journal.scratch(runner.token)["state"] == "held"
    assert runner.journal.scratch(runner.token)["candidate"] is None
    assert not runner.close()


@pytest.mark.parametrize("change", ["entry", "helper"])
def test_changes_during_hash_are_detected_before_seal(scratch_runner, monkeypatch, change):
    runner = scratch_runner
    scratch, launch = write_candidate(runner, helpers=("z.txt", "a.txt"))
    original = scratch._hash
    def hashing(held):
        result = original(held)
        if change == "entry":
            (scratch.path / "late.txt").write_bytes(b"during hash")
        else:
            helper = scratch.artifacts["a.txt"]
            os.write(helper.fd, b"helper changed during hash")
            os.fsync(helper.fd)
        return result
    monkeypatch.setattr(scratch, "_hash", hashing)
    with pytest.raises(Exception):
        scratch.seal_candidate(launch)
    assert runner.journal.scratch(runner.token)["candidate"] is None


def test_valid_multiple_helpers_and_outputs_have_canonical_order(scratch_runner):
    runner = scratch_runner
    scratch, launch = write_candidate(runner, helpers=("z.txt", "a.txt", "middle.txt"))
    candidate = scratch.seal_candidate(launch)
    record = runner.journal.scratch(runner.token)
    assert candidate["publication"] == "unpublished" and candidate["validation"] == "not_checked"
    assert [item["name"] for item in record["artifacts"]] == ["a.txt", "candidate.mp4", "middle.txt", "z.txt"]
    assert runner.close()
    assert runner.cleanup_evidence()["cleanup_complete"]
