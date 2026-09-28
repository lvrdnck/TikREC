"""External append-only retention journal boundaries."""

import json
import os

import pytest

from tikrec.retention_audit import AUDIT_SCHEMA, RetentionAudit
import tikrec.retention_audit as audit_module
from tests.test_retention_execute import fixture


def expected_posix_syncs(parent):
    """List containing directories from the volume root through the journal."""
    chain = (*reversed(parent.parents), parent)
    return [directory.parent for directory in chain if directory.parent != directory] + [parent]


def test_external_journal_appends_schema_events_and_refuses_hardlinks(tmp_path):
    root = tmp_path / "recordings"
    root.mkdir()
    path = tmp_path / "audit" / "history.jsonl"
    with RetentionAudit(root, path) as audit:
        audit.append("intent", "operation", session_id="session")
        audit.append("completed", "operation", deleted_count=0)
    records = [json.loads(line) for line in path.read_text().splitlines()]
    assert [item["event"] for item in records] == ["intent", "completed"]
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
    with RetentionAudit(root, path) as audit:
        audit.append("intent", "first", session_id="one")
    with RetentionAudit(root, path) as audit:
        audit.append("intent", "second", session_id="two")
    assert [json.loads(line)["operation_id"] for line in path.read_text().splitlines()] == [
        "first", "second"]


@pytest.mark.parametrize("failure", ["short", "raised"])
def test_torn_write_blocks_subsequent_audit_retry(tmp_path, failure):
    root = tmp_path / "recordings"
    root.mkdir()
    path = tmp_path / "audit" / "history.jsonl"

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
            audit.append("intent", "interrupted", session_id="one")
    with pytest.raises(ValueError, match="audit"):
        with RetentionAudit(root, path):
            pass
    assert path.read_bytes() and not path.read_bytes().endswith(b"\n")


def test_failed_audit_sync_does_not_poison_complete_existing_history(tmp_path, monkeypatch):
    root = tmp_path / "recordings"
    root.mkdir()
    path = tmp_path / "audit" / "history.jsonl"
    with RetentionAudit(root, path) as audit:
        audit.append("intent", "first", session_id="one")
    real_sync = os.fsync
    monkeypatch.setattr(audit_module.os, "fsync",
                        lambda _fd: (_ for _ in ()).throw(OSError("injected sync failure")))
    with pytest.raises(OSError, match="sync failure"):
        with RetentionAudit(root, path) as audit:
            audit.append("intent", "second", session_id="two")
    monkeypatch.setattr(audit_module.os, "fsync", real_sync)
    with RetentionAudit(root, path) as audit:
        audit.append("intent", "third", session_id="three")
    assert [json.loads(line)["operation_id"] for line in path.read_text().splitlines()] == [
        "first", "second", "third"]


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
        audit.append("intent", "first", session_id="one")
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
        audit.append("intent", "first", session_id="one")
    assert synced == expected_posix_syncs(parent)
    with RetentionAudit(root, path) as audit:
        audit.append("intent", "second", session_id="two")
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
