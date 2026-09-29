"""Quarantine must never remove a post-check replacement as an authorized file."""

import os
from pathlib import Path

import pytest

from tests.test_retention_execute import events, fixture
from tikrec.retention_execute import RetentionProgress


@pytest.mark.parametrize("kind", ["file", "directory"])
def test_replacement_after_final_check_is_refused_before_quarantine(
        tmp_path, monkeypatch, kind):
    import tikrec.retention_mutation as mutation

    root, parts, _, _, _, audit, run = fixture(tmp_path)
    original = mutation.check_fingerprint
    saved = root / f"saved-{kind}"
    replaced = False

    def swap_after_check(scope, item, volume):
        nonlocal replaced
        result = original(scope, item, volume)
        if not replaced and item.kind == kind:
            replaced = True
            path = scope / item.relative_path
            path.rename(saved)
            if kind == "file":
                path.write_bytes(b"unapproved replacement")
            else:
                path.mkdir()
        return result

    monkeypatch.setattr(mutation, "check_fingerprint", swap_after_check)
    with pytest.raises(ValueError, match="held artifact identity"):
        run()
    assert replaced and saved.exists() and (root / "alpha.mp4").exists()
    records = events(audit)
    assert records[-1]["event"] == "failed"
    assert not any(record["event"] == "completed" for record in records)
    attempted = records[-2]["path"]
    index = records[0]["order"].index(attempted)
    private = root / records[0]["quarantine_order"][index]
    assert not private.exists()
    replacement = root / attempted
    if kind == "file":
        assert replacement.read_bytes() == b"unapproved replacement"
    else:
        assert replacement.is_dir()


def test_failure_after_quarantine_leaves_auditable_nonresumable_artifact(
        tmp_path, monkeypatch):
    import tikrec.retention_execute as executor

    root, parts, _, _, _, audit, run = fixture(tmp_path)
    original = executor._sync_parent
    calls = 0

    def fail_first_sync(path: Path):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise OSError("injected quarantine sync failure")
        return original(path)

    monkeypatch.setattr(executor, "_sync_parent", fail_first_sync)
    with pytest.raises(OSError, match="quarantine sync"):
        run()
    records = events(audit)
    assert [event["event"] for event in records] == ["intent", "attempt", "failed"]
    private = root / records[0]["quarantine_order"][0]
    assert private.exists() and not (parts / "part-0001.flv").exists()
    monkeypatch.setattr(executor, "_sync_parent", original)
    with pytest.raises(ValueError, match="eligible"):
        run()
    assert (root / "alpha.mp4").exists()


@pytest.mark.parametrize("target", ["part", "output", "directory"])
def test_post_proof_substitution_is_denied_and_failure_preserves_object(
        tmp_path, monkeypatch, target):
    from tikrec.retention_windows import HeldArtifact

    root, parts, _, _, _, audit, run = fixture(tmp_path)
    prove = HeldArtifact.prove
    observed = []

    def replace_after_proof(self, digest):
        prove(self, digest)
        name = Path(self.expected.relative_path).name
        chosen = {"part": "part-0001.flv", "output": "alpha.mp4",
                  "directory": "alpha.parts"}[target]
        if name == chosen:
            observed.append(self.path)
            # This is the actual swap that used to succeed after a pathname hash.
            self.path.rename(root / "saved-authorized")
            pytest.fail("Windows allowed substitution of an exclusively held object")

    monkeypatch.setattr(HeldArtifact, "prove", replace_after_proof)
    with pytest.raises(PermissionError):
        run()
    assert len(observed) == 1 and observed[0].exists()
    assert not (root / "saved-authorized").exists()
    records = events(audit)
    assert records[-1]["event"] == "failed"
    assert not any(record["event"] == "completed" for record in records)
    assert not any(record["event"] == "deleted" and record["path"] == records[-1]["path"]
                   for record in records)
    if target != "output":
        assert (root / "alpha.mp4").exists()


@pytest.mark.parametrize("stage", ["before", "during"])
@pytest.mark.parametrize("target", ["file", "directory"])
def test_private_collision_preserves_both_objects(tmp_path, monkeypatch, stage, target):
    import tikrec.retention_mutation as mutation
    from tikrec.retention_windows import HeldArtifact

    root, _, _, _, _, audit, run = fixture(tmp_path)
    rename, check = HeldArtifact.rename, mutation.check_fingerprint
    occupied = []

    def occupy(path):
        if target == "directory":
            path.mkdir()
        else:
            path.write_bytes(b"unexpected occupant")
        occupied.append(path)

    def before(scope, item, volume):
        check(scope, item, volume)
        if stage == "before" and item.kind == target and not occupied:
            intent = events(audit)[0]
            index = intent["order"].index(item.relative_path)
            occupy(root / intent["quarantine_order"][index])

    def during(self, destination):
        if stage == "during" and self.expected.kind == target and not occupied:
            occupy(destination)
        rename(self, destination)

    monkeypatch.setattr(mutation, "check_fingerprint", before)
    monkeypatch.setattr(HeldArtifact, "rename", during)
    with pytest.raises((ValueError, OSError)):
        run()
    assert occupied[0].exists()
    if target == "file":
        assert occupied[0].read_bytes() == b"unexpected occupant"
    records = events(audit)
    assert records[-1]["event"] == "failed"
    assert (root / records[-1]["path"]).exists()
    assert (root / "alpha.mp4").exists()


def test_final_mp4_is_last_actual_handle_deletion(tmp_path, monkeypatch):
    from tikrec.retention_windows import HeldArtifact

    root, _, _, _, _, audit, run = fixture(tmp_path)
    delete, removed = HeldArtifact.delete, []

    def observe(self):
        delete(self)
        removed.append(self.expected.relative_path)

    monkeypatch.setattr(HeldArtifact, "delete", observe)
    run()
    assert removed == events(audit)[0]["order"]
    assert removed[-1] == "alpha.mp4" and not (root / "alpha.mp4").exists()


def test_original_reappears_after_quarantine_and_remains_preserved(tmp_path, monkeypatch):
    from tikrec.retention_windows import HeldArtifact

    root, parts, _, _, _, audit, run = fixture(tmp_path)
    prove = HeldArtifact.prove

    def reappear(self, digest):
        prove(self, digest)
        (root / self.expected.relative_path).write_bytes(b"new occupant")

    monkeypatch.setattr(HeldArtifact, "prove", reappear)
    with pytest.raises(ValueError, match="reappeared"):
        run()
    assert (parts / "part-0001.flv").read_bytes() == b"new occupant"
    records = events(audit)
    assert (root / records[0]["quarantine_order"][0]).exists()
    assert [record["event"] for record in records] == ["intent", "attempt", "failed"]


@pytest.mark.parametrize("name", ["original", "private"])
def test_reappearance_after_handle_close_is_preserved_and_audited_failed(
        tmp_path, monkeypatch, name):
    from tikrec.retention_windows import HeldArtifact

    root, _, _, _, _, audit, run = fixture(tmp_path)
    delete, occupants = HeldArtifact.delete, []

    def reappear(self):
        delete(self)
        path = root / self.expected.relative_path if name == "original" else self.path
        path.write_bytes(b"new occupant after removal")
        occupants.append(path)

    monkeypatch.setattr(HeldArtifact, "delete", reappear)
    with pytest.raises(ValueError, match="reappeared"):
        run()
    assert occupants[0].read_bytes() == b"new occupant after removal"
    assert [record["event"] for record in events(audit)] == ["intent", "attempt", "failed"]


@pytest.mark.skipif(os.name != "nt", reason="Windows exact-object deletion only")
def test_inner_primary_is_published_before_held_cleanup(tmp_path, monkeypatch):
    from tikrec.retention_windows import HeldArtifact

    root, parts, _, _, _, audit, run = fixture(tmp_path)
    original_exit = HeldArtifact.__exit__
    progress = RetentionProgress()

    def first_proof_fault(self, _digest):
        raise SystemExit("first proof fault")

    def later_cleanup_fault(self, *exc):
        original_exit(self, *exc)
        raise OSError("later held cleanup fault")

    monkeypatch.setattr(HeldArtifact, "prove", first_proof_fault)
    monkeypatch.setattr(HeldArtifact, "__exit__", later_cleanup_fault)
    with pytest.raises(SystemExit, match="first proof fault"):
        run(progress=progress)
    records = events(audit)
    assert type(progress.operation_error) is SystemExit
    assert str(progress.operation_error) == "first proof fault"
    assert [str(error) for error in progress.inner_cleanup_errors] == [
        "later held cleanup fault"]
    assert records[-1]["event"] == "failed"
    assert records[-1]["error_type"] == "SystemExit"
    assert (root / records[0]["quarantine_order"][0]).exists()
    assert not (parts / "part-0001.flv").exists()
    assert (root / "alpha.mp4").exists()
