"""External append-only retention journal boundaries."""

import json

import pytest

from tikrec.retention_audit import AUDIT_SCHEMA, RetentionAudit


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
