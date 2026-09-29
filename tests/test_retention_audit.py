"""External append-only retention journal boundaries."""

import json
import os
import uuid
from pathlib import Path

import pytest

from tikrec.retention_audit import AUDIT_SCHEMA, RetentionAudit
import tikrec.retention_audit as audit_module
from tests.test_retention_execute import fixture


ORDER = (str(Path("alpha.parts") / "part-0001.flv"),
         str(Path("alpha.parts") / "session.json"),
         "alpha.parts", "alpha.mp4")


def intent_fields(root, *, order=ORDER):
    """Build one journal-only schema-1 intent without relying on deleted media."""
    return dict(timestamp=2000000.0, root=str(root), session_id=str(uuid.uuid4()),
                creator="alpha", ended_at=1010.0, max_age_days=1,
                protected=False, protected_creators=[], order=list(order),
                artifacts=[dict(relative_path=path,
                                kind="directory" if path == "alpha.parts" else "file",
                                mode=0o40777 if path == "alpha.parts" else 0o100666,
                                size=1, device=1, inode=index + 1,
                                mtime_ns=1, ctime_ns=1, link_count=1,
                                attributes=0, volume=dict(platform="test",
                                                          point="test", identity="test"))
                           for index, path in enumerate(order)])


def new_operation():
    """Use the same canonical operation-ID shape as the executor."""
    return str(uuid.uuid4())


def expected_posix_syncs(parent):
    """List containing directories from the volume root through the journal."""
    chain = (*reversed(parent.parents), parent)
    return [directory.parent for directory in chain if directory.parent != directory] + [parent]


def test_external_journal_appends_schema_events_and_refuses_hardlinks(tmp_path):
    root = tmp_path / "recordings"
    root.mkdir()
    path = tmp_path / "audit" / "history.jsonl"
    operation = new_operation()
    with RetentionAudit(root, path) as audit:
        audit.append("intent", operation, **intent_fields(root))
        for artifact in ORDER:
            audit.append("attempt", operation, path=artifact)
            audit.append("deleted", operation, path=artifact)
        audit.append("completed", operation, deleted_count=len(ORDER))
    records = [json.loads(line) for line in path.read_text().splitlines()]
    assert [item["event"] for item in records] == [
        "intent", *[kind for _ in ORDER for kind in ("attempt", "deleted")], "completed"]
    assert all(item["schema_version"] == AUDIT_SCHEMA for item in records)
    (tmp_path / "audit-link").hardlink_to(path)
    with pytest.raises(ValueError, match="journal"):
        with RetentionAudit(root, path):
            pass


def test_journal_inside_root_refuses_before_creation(tmp_path):
    root = tmp_path / "recordings"
    root.mkdir()
    path = root / "audit" / "history.jsonl"
    with pytest.raises(ValueError, match="outside"):
        RetentionAudit(root, path)
    assert not path.exists()


def test_valid_existing_journal_accepts_another_complete_operation(tmp_path):
    root = tmp_path / "recordings"
    root.mkdir()
    path = tmp_path / "audit" / "history.jsonl"
    first, second = new_operation(), new_operation()
    with RetentionAudit(root, path) as audit:
        audit.append("intent", first, **intent_fields(root))
    with RetentionAudit(root, path) as audit:
        audit.append("intent", second, **intent_fields(root))
    assert [json.loads(line)["operation_id"] for line in path.read_text().splitlines()] == [
        first, second]


@pytest.mark.parametrize("failure", ["short", "raised"])
def test_torn_write_blocks_subsequent_audit_retry(tmp_path, failure):
    root = tmp_path / "recordings"
    root.mkdir()
    path = tmp_path / "audit" / "history.jsonl"
    operation = new_operation()

    class BrokenWrite:
        def __init__(self, handle):
            self.handle = handle

        def write(self, data):
            written = self.handle.write(data[:len(data) // 2])
            if failure == "raised":
                raise OSError("injected audit write failure")
            return written

        def close(self):
            self.handle.close()

    with pytest.raises(OSError):
        with RetentionAudit(root, path) as audit:
            audit.handle = BrokenWrite(audit.handle)
            audit.append("intent", operation, **intent_fields(root))
    with pytest.raises(ValueError, match="audit"):
        with RetentionAudit(root, path):
            pass
    assert path.read_bytes() and not path.read_bytes().endswith(b"\n")


def test_failed_audit_sync_does_not_poison_complete_existing_history(tmp_path, monkeypatch):
    root = tmp_path / "recordings"
    root.mkdir()
    path = tmp_path / "audit" / "history.jsonl"
    first, second, third = new_operation(), new_operation(), new_operation()
    with RetentionAudit(root, path) as audit:
        audit.append("intent", first, **intent_fields(root))
    real_sync = os.fsync
    monkeypatch.setattr(audit_module.os, "fsync",
                        lambda _fd: (_ for _ in ()).throw(OSError("injected sync failure")))
    with pytest.raises(OSError, match="sync failure"):
        with RetentionAudit(root, path) as audit:
            audit.append("intent", second, **intent_fields(root))
    monkeypatch.setattr(audit_module.os, "fsync", real_sync)
    with RetentionAudit(root, path) as audit:
        audit.append("intent", third, **intent_fields(root))
    assert [json.loads(line)["operation_id"] for line in path.read_text().splitlines()] == [
        first, second, third]


def test_posix_first_use_syncs_each_new_directory_entry_before_journal(
        tmp_path, monkeypatch):
    root = tmp_path / "recordings"
    root.mkdir()
    path = tmp_path / "audit" / "nested" / "history.jsonl"
    synced = []
    monkeypatch.setattr(audit_module, "_POSIX_SYNC", True)

    def observe(directory):
        if directory == tmp_path:
            assert path.parent.parent.is_dir() and not path.parent.exists()
        if directory == path.parent.parent:
            assert path.parent.is_dir() and not path.exists()
        synced.append(directory)

    monkeypatch.setattr(audit_module, "_sync_directory", observe)
    with RetentionAudit(root, path) as audit:
        audit.append("intent", new_operation(), **intent_fields(root))
    assert synced == expected_posix_syncs(path.parent)


def test_posix_existing_directories_resync_path_and_journal_entry(
        tmp_path, monkeypatch):
    root = tmp_path / "recordings"
    root.mkdir()
    parent = tmp_path / "audit" / "nested"
    parent.mkdir(parents=True)
    path = parent / "history.jsonl"
    synced = []
    monkeypatch.setattr(audit_module, "_POSIX_SYNC", True)
    monkeypatch.setattr(audit_module, "_sync_directory", synced.append)
    with RetentionAudit(root, path) as audit:
        audit.append("intent", new_operation(), **intent_fields(root))
    assert synced == expected_posix_syncs(parent)
    with RetentionAudit(root, path) as audit:
        audit.append("intent", new_operation(), **intent_fields(root))
    assert synced == expected_posix_syncs(parent) * 2


@pytest.mark.parametrize("prior", [
    b'{"schema_version":1',
    b'{"schema_version":1,"event":"intent","operation_id":"old"}',
    b'{"schema_version":1,"event":"intent","operation_id":"old"}\nnot json\n',
    b'{}\n',
    b'{"schema_version":1,"schema_version":1,"event":"intent",'
    b'"operation_id":"old"}\n',
    b'\xff\n',
])
def test_unreadable_existing_audit_blocks_before_deletion(tmp_path, prior):
    root, parts, _, _, _, audit, run = fixture(tmp_path)
    audit.parent.mkdir()
    audit.write_bytes(prior)
    with pytest.raises(ValueError, match="audit"):
        run()
    assert parts.exists() and (root / "alpha.mp4").exists()
    assert audit.read_bytes() == prior


@pytest.mark.parametrize("fail_at", ["ancestor", "journal"])
def test_audit_directory_sync_failure_preserves_session(tmp_path, monkeypatch, fail_at):
    root, parts, _, _, _, audit, run = fixture(tmp_path)
    monkeypatch.setattr(audit_module, "_POSIX_SYNC", True)
    calls = 0
    failing_call = (1 if fail_at == "ancestor" else len(expected_posix_syncs(audit.parent)))

    def fail_sync(_path):
        nonlocal calls
        calls += 1
        if calls == failing_call:
            raise OSError("audit directory sync failed")

    monkeypatch.setattr(audit_module, "_sync_directory", fail_sync)
    with pytest.raises(OSError, match="directory sync failed"):
        run()
    assert parts.exists() and (root / "alpha.mp4").exists()
    if fail_at == "ancestor":
        assert not audit.exists()
    else:
        assert audit.read_bytes() == b""
    synced = []
    monkeypatch.setattr(audit_module, "_sync_directory", synced.append)
    run()
    assert synced == expected_posix_syncs(audit.parent)
    assert not parts.exists() and not (root / "alpha.mp4").exists()


def test_entry_validation_fault_precedes_handle_close_fault(tmp_path, monkeypatch):
    root = tmp_path / "recordings"
    root.mkdir()
    path = tmp_path / "audit" / "history.jsonl"
    real_fdopen = audit_module.os.fdopen
    cleanup = []

    class ClosingFault:
        def __init__(self, handle):
            self.handle = handle

        def __getattr__(self, name):
            return getattr(self.handle, name)

        def close(self):
            self.handle.close()
            raise SystemExit("second audit handle close fault")

    def fdopen(*args, **kwargs):
        return ClosingFault(real_fdopen(*args, **kwargs))

    def first_validation(*_args):
        raise ValueError("first audit history validation fault")

    with monkeypatch.context() as scoped:
        scoped.setattr(audit_module.os, "fdopen", fdopen)
        scoped.setattr(audit_module, "_validate_history", first_validation)
        with pytest.raises(ValueError, match="first audit history validation fault"):
            with RetentionAudit(root, path, cleanup_errors=cleanup):
                pass
    assert path.read_bytes() == b""
    assert len(cleanup) == 1 and isinstance(cleanup[0], SystemExit)


def test_entry_descriptor_fault_precedes_descriptor_close_fault(tmp_path, monkeypatch):
    root = tmp_path / "recordings"
    root.mkdir()
    path = tmp_path / "audit" / "history.jsonl"
    real_fstat, real_close = audit_module.os.fstat, audit_module.os.close
    cleanup = []
    audit_descriptor = []

    def first_fstat(descriptor):
        audit_descriptor.append(descriptor)
        raise ValueError("first audit descriptor validation fault")

    def close_then_fault(descriptor):
        real_close(descriptor)
        if descriptor in audit_descriptor:
            raise SystemExit("second audit descriptor close fault")

    with monkeypatch.context() as scoped:
        scoped.setattr(audit_module.os, "fstat", first_fstat)
        scoped.setattr(audit_module.os, "close", close_then_fault)
        with pytest.raises(ValueError, match="first audit descriptor validation fault"):
            with RetentionAudit(root, path, cleanup_errors=cleanup):
                pass
    assert path.read_bytes() == b""
    assert len(cleanup) == 1 and isinstance(cleanup[0], SystemExit)


def test_audit_directory_sync_fault_precedes_close_fault(tmp_path, monkeypatch):
    real_open, real_close = audit_module.os.open, audit_module.os.close
    sentinel = tmp_path / "sync-descriptor"
    sentinel.write_bytes(b"")

    def first_sync(*_args):
        raise KeyboardInterrupt("first audit directory sync fault")

    def close_then_fault(descriptor):
        real_close(descriptor)
        raise SystemExit("second audit directory close fault")

    with monkeypatch.context() as scoped:
        scoped.setattr(audit_module.os, "open",
                       lambda _path, _flags: real_open(sentinel, os.O_RDONLY))
        scoped.setattr(audit_module.os, "fsync", first_sync)
        scoped.setattr(audit_module.os, "close", close_then_fault)
        with pytest.raises(KeyboardInterrupt, match="first audit directory sync fault") as caught:
            audit_module._sync_directory(tmp_path)
    assert any("second audit directory close fault" in note
               for note in caught.value.__notes__)
