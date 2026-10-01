"""Native managed deletion keeps exclusion, byte binding, failure order and MP4 last."""

import json
import os

import pytest

from tests.managed_fixture import managed_fixture, service_action, execute


def records(state):
    """Read this disposable root's sole audit history."""
    files = list((state / "retention-audit").glob("*.jsonl"))
    return [] if not files else [json.loads(line) for line in files[0].read_text().splitlines()]


def test_native_order_and_owner_exclusion_during_each_removal(managed_fixture):
    _, root, parts, state, _, session_id = managed_fixture
    def run(authority, connection):
        from tikrec.retention_linux import HeldArtifact
        original = HeldArtifact.prove
        def prove(held, digest):
            original(held, digest)
            # Probe the private namespace after hashing as well as the original
            # namespace before mutation; reader processes cannot close the gap.
            connection.send(("owner-probe", str(authority.root)))
            assert connection.recv() == "probed"
        HeldArtifact.prove = prove
        def witness(_path):
            connection.send(("owner-probe", str(authority.root)))
            assert connection.recv() == "probed"
        execute(authority, session_id, before_mutation=witness)
    service_action(managed_fixture, run)
    events = records(state)
    assert events[-1]["event"] == "completed"
    assert [event["path"] for event in events if event["event"] == "deleted"] == events[0]["order"]
    assert events[0]["order"][-3:] == ["alpha.parts/session.json", "alpha.parts", "alpha.mp4"]
    assert not parts.exists() and not (root / "alpha.mp4").exists()


@pytest.mark.parametrize("failure", ["occupied", "late_child", "wrong_bytes", "reappearance",
                                    "job", "policy", "interruption", "sync"])
def test_first_failure_preserves_final_mp4_and_no_completion(managed_fixture, monkeypatch, failure):
    from tikrec.retention_linux import HeldArtifact
    from tikrec.job_state import JobState, JobStateStore
    _, root, parts, state, _, session_id = managed_fixture
    original_rename, original_prove, original_sync = (HeldArtifact.rename,
                                                     HeldArtifact.prove, HeldArtifact.sync_parent)
    def rename(self, destination):
        if failure == "occupied":
            destination.write_bytes(b"occupied quarantine")
        return original_rename(self, destination)
    def prove(self, digest):
        if failure == "wrong_bytes":
            self.path.write_bytes(b"changed authorized bytes")
        result = original_prove(self, digest)
        if failure == "reappearance":
            (root / self.expected.relative_path).write_bytes(b"late original")
        if failure == "late_child" and self.expected.kind == "directory":
            (self.path / "late.flv").write_bytes(b"late trusted child")
        return result
    def sync(self):
        if failure == "sync":
            raise OSError("injected pinned-parent sync failure")
        return original_sync(self)
    monkeypatch.setattr(HeldArtifact, "rename", rename)
    monkeypatch.setattr(HeldArtifact, "prove", prove)
    monkeypatch.setattr(HeldArtifact, "sync_parent", sync)
    def run(authority, _):
        def witness(_path):
            if failure == "interruption":
                raise KeyboardInterrupt
            if failure == "policy":
                document = json.loads(authority.config_path.read_text())
                document["retention_max_age_days"] = 100
                authority.config_path.write_text(json.dumps(document))
            if failure == "job":
                # Inject bytes as a faulty trusted actor, bypassing the gate that
                # the real JobStateStore.save entry point now requires.
                from dataclasses import asdict
                job = JobState(session_id=session_id, source_url="https://www.tiktok.com/@alpha/live",
                               output_path=str(root / "alpha.mp4"), parts_directory=str(parts),
                               started_at=1000, state="completed", ended_at=1010)
                authority.job_paths[1].write_text(json.dumps(asdict(job)))
        with pytest.raises((ValueError, OSError, KeyboardInterrupt)):
            execute(authority, session_id, before_mutation=witness)
    service_action(managed_fixture, run)
    events = records(state)
    assert events[-1]["event"] == "failed"
    assert not any(event["event"] == "completed" for event in events)
    assert (root / "alpha.mp4").exists()


def test_active_slot_or_writable_descriptor_refuses_before_intent(managed_fixture):
    def run(authority, _):
        authority.quiescent = lambda: False
        with pytest.raises(ValueError, match="slots"):
            execute(authority, managed_fixture[5])
        authority.quiescent = lambda: True
        with (authority.root / "alpha.mp4").open("ab"):
            with pytest.raises(ValueError, match="writable descriptor"):
                execute(authority, managed_fixture[5])
    service_action(managed_fixture, run)
    assert records(managed_fixture[3]) == []


def test_writable_mapping_without_descriptor_refuses_before_intent(managed_fixture):
    def run(authority, _):
        import ctypes
        library = ctypes.CDLL(None, use_errno=True)
        library.mmap.restype = ctypes.c_void_p
        descriptor = os.open(authority.root / "alpha.mp4", os.O_RDWR)
        size = os.fstat(descriptor).st_size
        address = library.mmap(None, size, 3, 1, descriptor, 0)
        os.close(descriptor)
        assert address != ctypes.c_void_p(-1).value
        try:
            with pytest.raises(ValueError, match="writable mapping"):
                execute(authority, managed_fixture[5])
        finally:
            assert library.munmap(ctypes.c_void_p(address), size) == 0
    service_action(managed_fixture, run)
    assert records(managed_fixture[3]) == []


@pytest.mark.parametrize("kind", ["file", "directory"])
def test_private_substitution_after_proof_preserves_both_objects(managed_fixture, monkeypatch, kind):
    from tikrec.retention_linux import HeldArtifact
    original = HeldArtifact.prove
    def substitute(held, digest):
        original(held, digest)
        if held.expected.kind == kind:
            held.path.rename(held.path.with_name("saved-authorized-object"))
            if kind == "directory":
                held.path.mkdir()
            else:
                held.path.write_bytes(b"unapproved replacement")
    monkeypatch.setattr(HeldArtifact, "prove", substitute)
    def run(authority, _):
        with pytest.raises(ValueError, match="identity changed"):
            execute(authority, managed_fixture[5])
    service_action(managed_fixture, run)
    events = records(managed_fixture[3])
    relative = events[-1]["path"]
    index = events[0]["order"].index(relative)
    private = managed_fixture[1] / events[0]["quarantine_order"][index]
    assert private.exists() and private.with_name("saved-authorized-object").exists()
    assert events[-1]["event"] == "failed" and (managed_fixture[1] / "alpha.mp4").exists()


def test_first_proof_failure_is_not_replaced_by_native_close_fault(managed_fixture, monkeypatch):
    from tikrec.retention_linux import HeldArtifact
    from tikrec.retention_execute import RetentionProgress
    original_close = HeldArtifact.close
    def prove(held, digest):
        raise ValueError("first proof failure")
    def close(held):
        original_close(held)
        raise OSError("secondary native close failure")
    monkeypatch.setattr(HeldArtifact, "prove", prove)
    monkeypatch.setattr(HeldArtifact, "close", close)
    def run(authority, _):
        progress = RetentionProgress()
        with pytest.raises(ValueError, match="first proof failure"):
            execute(authority, managed_fixture[5], progress=progress)
        assert str(progress.operation_error) == "first proof failure"
        assert any("secondary native close" in str(error) for error in progress.inner_cleanup_errors)
    service_action(managed_fixture, run)
    events = records(managed_fixture[3])
    assert events[-1]["event"] == "failed" and events[-1]["error_type"] == "ValueError"
    assert (managed_fixture[1] / "alpha.mp4").exists()


@pytest.mark.parametrize("kind", ["file", "directory"])
def test_atomic_collision_created_inside_rename_preserves_both(managed_fixture, monkeypatch, kind):
    from tikrec.retention_linux import HeldArtifact
    original = HeldArtifact.rename
    def collide(held, destination):
        if held.expected.kind == kind:
            if kind == "directory":
                destination.mkdir()
            else:
                destination.write_bytes(b"unapproved occupant")
        return original(held, destination)
    monkeypatch.setattr(HeldArtifact, "rename", collide)
    def run(authority, _):
        with pytest.raises(OSError):
            execute(authority, managed_fixture[5])
    service_action(managed_fixture, run)
    events = records(managed_fixture[3])
    attempted = events[-1]["path"]
    assert (managed_fixture[1] / attempted).exists()
    index = events[0]["order"].index(attempted)
    assert (managed_fixture[1] / events[0]["quarantine_order"][index]).exists()
    assert (managed_fixture[1] / "alpha.mp4").exists()


@pytest.mark.parametrize("name", ["original", "private"])
def test_reappearance_after_removal_is_preserved_and_failed(managed_fixture, monkeypatch, name):
    from tikrec.retention_linux import HeldArtifact
    original = HeldArtifact.delete
    def reappear(held):
        original(held)
        path = held.path if name == "private" else managed_fixture[1] / held.expected.relative_path
        path.write_bytes(b"unapproved reappearance")
    monkeypatch.setattr(HeldArtifact, "delete", reappear)
    def run(authority, _):
        with pytest.raises(ValueError, match="reappeared"):
            execute(authority, managed_fixture[5])
    service_action(managed_fixture, run)
    events = records(managed_fixture[3])
    assert [event["event"] for event in events] == ["intent", "attempt", "failed"]
    assert (managed_fixture[1] / "alpha.mp4").exists()
