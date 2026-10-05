"""Native disposable writer evidence never implies media validity or publication."""

import os
import sys
from pathlib import Path
from dataclasses import asdict

import pytest

from tests.owned_process_helpers import managed_process
from tests.sealed_input_helpers import hashes, sealed
from tikrec.attempt_coordinator import AttemptCoordinator


pytestmark = pytest.mark.skipif(os.name != "nt", reason="native scratch ownership requires Windows")


def process_factory(make):
    """Retain independent exact-job cleanup for every contained child."""
    def create(session_id, token):
        child = make()
        child.session_id, child.attempt_token = session_id, token
        return child
    return create


def test_candidate_requires_durable_writer_receipts_and_stays_unpublished(sealed, managed_process):
    owner, bridge, original = sealed
    before = hashes(owner.root)
    runner = AttemptCoordinator(owner, process_factory=process_factory(managed_process))
    try:
        claim = runner.claim()
        scratch = runner.reserve_scratch(helpers=("manifest.txt",))
        row = owner.journal.owned_attempt(runner.token)
        assert row["scratch"]["state"] == "bound"
        assert row["scratch"]["intent"]["seal_hash"] == original["seal_hash"]
        assert scratch.path != Path(bridge.intent.output_path)
        assert scratch.path != Path(bridge.intent.parts_path)
        source_write = ("from pathlib import Path;"
                        "Path('candidate.mp4').write_bytes(b'nonempty synthetic candidate');"
                        "Path('manifest.txt').write_text('declared helper')")
        evidence = scratch.run_writer(Path(sys._base_executable), ["-c", source_write], timeout=10,
                                      outputs=("candidate.mp4", "manifest.txt"))
        child = runner.children[-1]
        assert evidence.state == "confirmed_exited" and child["cleanup_recorded"]
        candidate = scratch.seal_candidate(child["launch"])
        assert candidate["validation"] == "not_checked"
        assert candidate["publication"] == "unpublished"
        assert candidate["size"] == len(b"nonempty synthetic candidate")
        assert candidate["execution"]["input_decode"] == "unknown"
        row = owner.journal.owned_attempt(runner.token)
        assert row["scratch"]["state"] == "candidate_ready"
        assert row["scratch"]["candidate"]["sha256"] == candidate["sha256"]
        session = owner.journal.session(bridge.intent.session_id)
        assert session["phase"] == "running" and session["task"]["state"] == "running"
        assert len(owner.journal.status()["units"]) == 1
        assert not Path(bridge.intent.output_path).exists()
        after = {name: value for name, value in hashes_without_scratch(owner.root).items()}
        assert all(after[name] == value for name, value in before.items())
        replacement = owner.reserve(owner.root / "replacement.mp4", "replacement", "456",
                                    started_at=200.0)
        assert replacement.intent.output_path.endswith("replacement.mp4")
        assert len(owner.journal.status()["units"]) == 2
        assert runner.close()
        retained = owner.journal.scratch(runner.token)
        assert retained["candidate"]["publication"] == "unpublished"
        assert owner.journal.session(bridge.intent.session_id)["task"]["state"] == "running"
    finally:
        runner.close()


def test_mkdir_ack_gap_is_held_without_adopting_preexisting_directory(sealed):
    owner, _, _ = sealed
    runner = AttemptCoordinator(owner)
    runner.claim()
    path = owner.root / f".tikrec-attempt-{runner.token}"
    path.mkdir()
    sentinel = path / "owner.txt"
    sentinel.write_text("preexisting owner")
    try:
        with pytest.raises(Exception):
            runner.reserve_scratch()
        row = owner.journal.owned_attempt(runner.token)
        assert row["scratch"]["state"] == "held"
        assert row["scratch"]["workspace_identity"] is None
        assert row["scratch"]["hold_reason"] is not None
        assert sentinel.read_text() == "preexisting owner"
        assert runner.scratch.workspace is None
    finally:
        runner.close()
        sentinel.unlink()
        path.rmdir()


def test_failure_after_atomic_create_keeps_unbound_native_owner(sealed):
    owner, _, _ = sealed
    fired = []
    def fault(point):
        if point == "after_scratch_create" and not fired:
            fired.append(point)
            raise RuntimeError("simulated death after mkdir")
    runner = AttemptCoordinator(owner, fault=fault)
    runner.claim()
    try:
        with pytest.raises(Exception):
            runner.reserve_scratch()
        scratch = owner.journal.scratch(runner.token)
        assert scratch["state"] == "held" and scratch["workspace_identity"] is None
        assert runner.scratch.created and runner.scratch.workspace is not None
        observed = asdict(runner.scratch.workspace.identity)
        expected = owner.journal.owned_attempt(runner.token)["scratch"]["intent"]["workspace"]
        assert observed["volume"] == expected["volume"]
        assert list(observed["components"]) == expected["components"]
    finally:
        runner.close()
        if runner.scratch is not None and runner.scratch.workspace is not None:
            runner.scratch.workspace.close()
        if runner.scratch is not None and runner.scratch.path.exists():
            runner.scratch.path.rmdir()


def test_candidate_created_before_ready_commit_is_preserved_as_held(sealed, managed_process):
    owner, _, _ = sealed
    fired = []
    def fault(point):
        if point == "after_candidate_created" and not fired:
            fired.append(point)
            raise RuntimeError("simulated stop before candidate-ready commit")
    runner = AttemptCoordinator(owner, process_factory=process_factory(managed_process), fault=fault)
    runner.claim()
    scratch = runner.reserve_scratch()
    try:
        scratch.run_writer(Path(sys._base_executable), ["-c",
            "from pathlib import Path;Path('candidate.mp4').write_bytes(b'partial candidate')"], timeout=10)
        launch = runner.children[-1]["launch"]
        with pytest.raises(RuntimeError, match="simulated stop"):
            scratch.seal_candidate(launch)
        record = owner.journal.scratch(runner.token)
        assert record["state"] == "held" and record["candidate"] is None
        assert (scratch.path / "candidate.mp4").exists()
        with pytest.raises(Exception):
            runner.run_writer_child(Path(sys._base_executable), ["-c", "pass"],
                                    cwd=scratch.path, phase="writer", timeout=5)
    finally:
        runner.close()
        for held in scratch.artifacts.values():
            held.close()
        if scratch.workspace is not None:
            scratch.workspace.close()
        for path in scratch.path.iterdir():
            path.unlink()
        scratch.path.rmdir()


@pytest.mark.parametrize("boundary,expected", [("after_scratch_intent", "held"),
    ("after_scratch_bind", "held"), ("after_artifact_bind", "held"),
    ("before_candidate_ready", "held"), ("after_candidate_ready", "candidate_ready")])
def test_scratch_crash_boundaries_keep_exact_current_facts(sealed, managed_process, boundary, expected):
    owner, _, _ = sealed
    fired = []
    def fault(point):
        if point == boundary and not fired:
            fired.append(point)
            raise RuntimeError("simulated boundary interruption")
    runner = AttemptCoordinator(owner, process_factory=process_factory(managed_process), fault=fault)
    runner.claim()
    try:
        with pytest.raises(Exception):
            scratch = runner.reserve_scratch()
            scratch.run_writer(Path(sys._base_executable), ["-c",
                "from pathlib import Path;Path('candidate.mp4').write_bytes(b'candidate')"], timeout=10)
            scratch.seal_candidate(runner.children[-1]["launch"])
        record = owner.journal.scratch(runner.token)
        assert fired == [boundary]
        assert record["state"] == expected
        assert (record["candidate"] is not None) == (expected == "candidate_ready")
        assert len(owner.journal.child_history(runner.token)) <= 1
        assert owner.journal.status()["tasks"][0]["state"] == "running"
        assert len(owner.journal.status()["units"]) == 1
    finally:
        runner.close()
        if runner.scratch is not None and not runner.scratch.candidate_ready:
            for held in runner.scratch.artifacts.values():
                held.close()
            if runner.scratch.workspace is not None:
                runner.scratch.workspace.close()
            if runner.scratch.path.exists():
                for path in runner.scratch.path.iterdir():
                    path.unlink()
                runner.scratch.path.rmdir()


def test_external_candidate_creation_between_identity_and_resume_is_refused(sealed, managed_process):
    owner, _, _ = sealed
    fired = []
    runner = None
    def fault(point):
        if point == "before_resume_fence" and not fired:
            fired.append(point)
            (runner.scratch.path / "candidate.mp4").write_bytes(b"external collision")
    runner = AttemptCoordinator(owner, process_factory=process_factory(managed_process), fault=fault)
    runner.claim()
    scratch = runner.reserve_scratch()
    try:
        with pytest.raises(Exception):
            scratch.run_writer(Path(sys._base_executable), ["-c", "raise SystemExit(0)"], timeout=10)
        record = owner.journal.scratch(runner.token)
        assert fired and record["state"] == "held" and record["candidate"] is None
        assert (scratch.path / "candidate.mp4").read_bytes() == b"external collision"
        child = owner.journal.owned_attempt(runner.token)["child"]
        assert child["identity"] is not None and child["exit"] is not None
        assert child["cleanup"] == 1
    finally:
        runner.close()
        (scratch.path / "candidate.mp4").unlink()
        scratch.workspace.close()
        scratch.path.rmdir()


def test_writer_launch_identity_prevents_same_attempt_retry(sealed, managed_process):
    owner, _, _ = sealed
    runner = AttemptCoordinator(owner, process_factory=process_factory(managed_process))
    runner.claim()
    scratch = runner.reserve_scratch()
    try:
        scratch.run_writer(Path(sys._base_executable), ["-c", "pass"], timeout=10)
        prior = runner.children[-1]["launch"]
        with pytest.raises(Exception):
            scratch.run_writer(Path(sys._base_executable), ["-c",
                "from pathlib import Path;Path('candidate.mp4').write_bytes(b'retry')"], timeout=10)
        row = owner.journal.owned_attempt(runner.token)
        assert row["scratch"]["writer_launch"] == prior
        assert len(owner.journal.child_history(runner.token)) == 1
        assert row["scratch"]["state"] == "held"
        assert not (scratch.path / "candidate.mp4").exists()
    finally:
        runner.close()
        scratch.workspace.close()
        scratch.path.rmdir()


def test_unavailable_reservation_receipt_never_starts_filesystem_work(sealed, monkeypatch):
    from tikrec.attempt_coordinator import AttemptError
    from tikrec.session_journal_types import JournalError
    owner, _, _ = sealed
    runner = AttemptCoordinator(owner)
    runner.claim()
    expected = owner.root / f".tikrec-attempt-{runner.token}"
    fired = []
    def fault(kind, boundary):
        if kind == "reserve_scratch" and boundary == "after_commit" and not fired:
            fired.append(kind)
            raise OSError("reservation acknowledgement lost")
    def unavailable(_operation):
        raise JournalError("receipt lookup unavailable")
    owner.journal._fault = fault
    monkeypatch.setattr(owner.journal, "operation", unavailable)
    try:
        with pytest.raises(AttemptError):
            runner.reserve_scratch()
        row = owner.journal.owned_attempt(runner.token)
        assert fired and row["scratch"]["state"] == "reserved"
        assert not expected.exists() and not runner.children
    finally:
        owner.journal._fault = None
        monkeypatch.undo()
        runner.close()


def hashes_without_scratch(root):
    """Hash original H and lifecycle evidence without reopening protected candidate files."""
    import hashlib
    return {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in Path(root).rglob("*") if path.is_file()
            and path.name != ".tikrec-lifecycle.lock"
            and not any(part.startswith(".tikrec-attempt-") for part in path.parts)}
