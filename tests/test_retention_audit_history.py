"""Schema-1 retention history must represent coherent ordered operations."""

import json

import pytest

from tests.test_retention_audit import intent_fields, new_operation
from tests.test_retention_execute import fixture
from tikrec.retention_audit import RetentionAudit


def event(kind, operation, **fields):
    """Build one complete JSONL event for a synthetic historical operation."""
    return {"schema_version": 1, "event": kind, "operation_id": operation, **fields}


def history(root, case):
    """Return a two-artifact history with one selected fault or crash boundary."""
    operation = new_operation()
    intent = event("intent", operation, **intent_fields(root, order=("one.flv", "two.mp4")))
    attempt_one = event("attempt", operation, path="one.flv")
    deleted_one = event("deleted", operation, path="one.flv")
    attempt_two = event("attempt", operation, path="two.mp4")
    deleted_two = event("deleted", operation, path="two.mp4")
    completed = event("completed", operation, deleted_count=2)
    failed = event("failed", operation, path="two.mp4", error_type="OSError")
    if case == "orphan_completed":
        return [completed]
    if case == "orphan_attempt":
        return [attempt_one]
    if case == "orphan_deleted":
        return [deleted_one]
    if case == "orphan_failed":
        return [failed]
    if case == "duplicate_intent":
        return [intent, intent]
    if case == "reused_id":
        return [intent, attempt_one, deleted_one, attempt_two, deleted_two,
                completed, intent]
    if case == "wrong_path":
        return [intent, attempt_two]
    if case == "wrong_artifact_order":
        intent["artifacts"].reverse()
        return [intent]
    if case == "unsafe_intent_path":
        intent["order"][0] = "../one.flv"
        intent["artifacts"][0]["relative_path"] = "../one.flv"
        return [intent]
    if case == "invalid_recovery_hash":
        intent["recovery_byte_hashes"] = {"one.flv": "not-a-digest"}
        return [intent]
    if case == "extra_attempt_field":
        attempt_one["error_type"] = "OSError"
        return [intent, attempt_one]
    if case == "deleted_without_attempt":
        return [intent, deleted_one]
    if case == "duplicate_deletion":
        return [intent, attempt_one, deleted_one, deleted_one]
    if case == "duplicate_attempt":
        return [intent, attempt_one, attempt_one]
    if case == "mismatched_result":
        return [intent, attempt_one, deleted_two]
    if case == "premature_completed":
        return [intent, attempt_one, deleted_one, completed]
    if case == "duplicate_terminal":
        return [intent, attempt_one, deleted_one, attempt_two, deleted_two,
                completed, completed]
    if case == "contradictory_terminal":
        return [intent, attempt_one, deleted_one, failed, completed]
    if case == "missing_failed_type":
        return [intent, event("failed", operation, path="one.flv")]
    if case == "wrong_deleted_count":
        return [intent, attempt_one, deleted_one, attempt_two, deleted_two,
                event("completed", operation, deleted_count=1)]
    if case == "bool_deleted_count":
        return [intent, attempt_one, deleted_one, attempt_two, deleted_two,
                event("completed", operation, deleted_count=True)]
    if case == "completed":
        return [intent, attempt_one, deleted_one, attempt_two, deleted_two, completed]
    if case == "failed":
        return [intent, attempt_one, deleted_one, attempt_two, failed]
    if case == "failed_before_attempt":
        return [intent, attempt_one, deleted_one, failed]
    if case == "failed_after_deleted":
        return [intent, attempt_one, deleted_one,
                event("failed", operation, path="one.flv", error_type="OSError")]
    if case == "intent_only":
        return [intent]
    if case == "unmatched_attempt":
        return [intent, attempt_one]
    if case == "partial_crash":
        return [intent, attempt_one, deleted_one]
    if case == "multiple":
        other = new_operation()
        return [intent, attempt_one, deleted_one, attempt_two, deleted_two,
                completed, event("intent", other, **intent_fields(root)),
                event("attempt", other, path="alpha.mp4")]
    raise AssertionError(case)


@pytest.mark.parametrize("case", [
    "orphan_completed", "orphan_attempt", "orphan_deleted", "orphan_failed",
    "duplicate_intent", "reused_id", "wrong_path", "wrong_artifact_order",
    "unsafe_intent_path", "invalid_recovery_hash", "extra_attempt_field",
    "deleted_without_attempt", "duplicate_deletion", "duplicate_attempt",
    "mismatched_result", "premature_completed", "duplicate_terminal",
    "contradictory_terminal", "missing_failed_type", "wrong_deleted_count",
    "bool_deleted_count",
])
def test_semantically_invalid_prior_history_blocks_deletion(tmp_path, case):
    root, parts, _, _, _, audit, run = fixture(tmp_path)
    audit.parent.mkdir()
    prior = b"".join((json.dumps(item) + "\n").encode() for item in history(root, case))
    audit.write_bytes(prior)
    with pytest.raises(ValueError, match="audit"):
        run()
    assert parts.exists() and (root / "alpha.mp4").exists()
    assert audit.read_bytes() == prior


@pytest.mark.parametrize("case", [
    "completed", "failed", "failed_before_attempt", "failed_after_deleted", "intent_only",
    "unmatched_attempt", "partial_crash", "multiple",
])
def test_coherent_completed_failed_and_crash_histories_allow_new_operation(
        tmp_path, case):
    root, parts, _, _, _, audit, run = fixture(tmp_path)
    audit.parent.mkdir()
    prior = b"".join((json.dumps(item) + "\n").encode() for item in history(root, case))
    audit.write_bytes(prior)
    run()
    assert not parts.exists() and not (root / "alpha.mp4").exists()
    assert audit.read_bytes().startswith(prior)


def test_failed_after_durable_deleted_line_remains_readable(tmp_path, monkeypatch):
    root, parts, _, _, _, audit, run = fixture(tmp_path)
    original_append = RetentionAudit.append

    def fail_after_deleted(self, kind, operation, **fields):
        original_append(self, kind, operation, **fields)
        if kind == "deleted":
            raise OSError("injected post-write sync failure")

    monkeypatch.setattr(RetentionAudit, "append", fail_after_deleted)
    with pytest.raises(OSError, match="sync failure"):
        run()
    monkeypatch.setattr(RetentionAudit, "append", original_append)
    with RetentionAudit(root, audit):
        pass
    records = [json.loads(line) for line in audit.read_text().splitlines()]
    assert [record["event"] for record in records] == [
        "intent", "attempt", "deleted", "failed"]
    assert parts.exists() and (root / "alpha.mp4").exists()
