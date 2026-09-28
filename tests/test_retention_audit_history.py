"""Schema-1 retention history must represent coherent ordered operations."""

import json
import os
import copy
from pathlib import Path

import pytest

from tests.test_retention_audit import ORDER, intent_fields, new_operation
from tests.test_retention_execute import fixture
from tikrec.retention_audit import RetentionAudit
from tikrec.retention_audit_history import AuditHistory


def event(kind, operation, **fields):
    """Build one complete JSONL event for a synthetic historical operation."""
    return {"schema_version": 1, "event": kind, "operation_id": operation, **fields}


def history(root, case):
    """Return a genuine artifact order with one selected fault or crash boundary."""
    operation = new_operation()
    intent = event("intent", operation, **intent_fields(root))
    attempts = [event("attempt", operation, path=path) for path in ORDER]
    deletions = [event("deleted", operation, path=path) for path in ORDER]
    attempt_one, attempt_two = attempts[:2]
    deleted_one, deleted_two = deletions[:2]
    all_deleted = [item for pair in zip(attempts, deletions) for item in pair]
    completed = event("completed", operation, deleted_count=len(ORDER))
    failed = event("failed", operation, path=ORDER[1], error_type="OSError")
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
        return [intent, *all_deleted, completed, intent]
    if case == "wrong_path":
        return [intent, attempt_two]
    if case == "foreign_root":
        intent["root"] = str(root.parent / "another-recording-root")
        return [intent]
    if case == "root_alias":
        intent["root"] = str(root / ".." / root.name)
        return [intent]
    if case == "final_mp4_first":
        intent["order"].insert(0, intent["order"].pop())
        intent["artifacts"].insert(0, intent["artifacts"].pop())
        return [intent]
    if case == "directory_before_child":
        intent["order"].insert(0, intent["order"].pop(-2))
        intent["artifacts"].insert(0, intent["artifacts"].pop(-2))
        return [intent]
    if case == "wrong_child_parent":
        intent["order"][0] = "other.parts/part-0001.flv"
        intent["artifacts"][0]["relative_path"] = intent["order"][0]
        return [intent]
    if case == "wrong_artifact_kind":
        intent["artifacts"][-2]["kind"] = "file"
        return [intent]
    if case == "cross_volume":
        intent["artifacts"][0]["volume"]["identity"] = "another-volume"
        return [intent]
    if case == "multiply_linked":
        intent["artifacts"][0]["link_count"] = 2
        return [intent]
    if case == "resumed_after_later_intent":
        other = new_operation()
        return [intent, event("intent", other, **intent_fields(root)), attempt_one]
    if case == "wrong_artifact_order":
        intent["artifacts"].reverse()
        return [intent]
    if case == "unsafe_intent_path":
        intent["order"][0] = "../part-0001.flv"
        intent["artifacts"][0]["relative_path"] = "../part-0001.flv"
        return [intent]
    if case == "invalid_recovery_hash":
        intent["recovery_byte_hashes"] = {ORDER[0]: "not-a-digest"}
        return [intent]
    if case == "hash_on_control":
        intent["recovery_byte_hashes"] = {ORDER[1]: "0" * 64}
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
        return [intent, *all_deleted, completed, completed]
    if case == "contradictory_terminal":
        return [intent, attempt_one, deleted_one, failed, completed]
    if case == "advance_after_deleted_failed":
        return [intent, attempt_one, deleted_one,
                event("failed", operation, path=ORDER[0], error_type="OSError"),
                attempt_two]
    if case == "missing_failed_type":
        return [intent, event("failed", operation, path=ORDER[0])]
    if case == "wrong_deleted_count":
        return [intent, *all_deleted, event("completed", operation, deleted_count=1)]
    if case == "bool_deleted_count":
        return [intent, *all_deleted, event("completed", operation, deleted_count=True)]
    if case == "completed":
        return [intent, *all_deleted, completed]
    if case == "failed":
        return [intent, attempt_one, deleted_one, attempt_two, failed]
    if case == "failed_before_attempt":
        return [intent, attempt_one, deleted_one, failed]
    if case == "failed_after_deleted":
        return [intent, attempt_one, deleted_one,
                event("failed", operation, path=ORDER[0], error_type="OSError")]
    if case == "intent_only":
        return [intent]
    if case == "unmatched_attempt":
        return [intent, attempt_one]
    if case == "partial_crash":
        return [intent, attempt_one, deleted_one]
    if case == "multiple":
        other = new_operation()
        return [intent, *all_deleted, completed,
                event("intent", other, **intent_fields(root)),
                event("attempt", other, path=ORDER[0])]
    if case == "incomplete_then_independent":
        other = new_operation()
        return [intent, attempt_one, event("intent", other, **intent_fields(root)),
                *[event(kind, other, path=path) for path in ORDER
                  for kind in ("attempt", "deleted")],
                event("completed", other, deleted_count=len(ORDER))]
    if case == "multiple_terminal_and_incomplete":
        second, third = new_operation(), new_operation()
        return [intent, *all_deleted, completed,
                event("intent", second, **intent_fields(root)),
                event("failed", second, path=ORDER[0], error_type="OSError"),
                event("intent", third, **intent_fields(root)),
                event("attempt", third, path=ORDER[0])]
    if case == "windows_case_alias":
        assert os.name == "nt"
        intent["root"] = str(root).swapcase()
        return [intent]
    raise AssertionError(case)


@pytest.mark.parametrize("case", [
    "orphan_completed", "orphan_attempt", "orphan_deleted", "orphan_failed",
    "duplicate_intent", "reused_id", "wrong_path", "wrong_artifact_order",
    "foreign_root", "root_alias", "final_mp4_first", "directory_before_child",
    "wrong_child_parent", "wrong_artifact_kind", "cross_volume", "multiply_linked",
    "resumed_after_later_intent", "advance_after_deleted_failed",
    "unsafe_intent_path", "invalid_recovery_hash", "hash_on_control",
    "extra_attempt_field",
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
    "unmatched_attempt", "partial_crash", "multiple", "incomplete_then_independent",
    "multiple_terminal_and_incomplete",
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


@pytest.mark.skipif(os.name != "nt", reason="Windows roots are case-insensitive")
def test_windows_case_alias_of_same_root_remains_valid(tmp_path):
    root, parts, _, _, _, audit, run = fixture(tmp_path)
    audit.parent.mkdir()
    audit.write_text("".join(json.dumps(item) + "\n" for item in
                             history(root, "windows_case_alias")))
    run()
    assert not parts.exists()


def test_real_recovery_and_connection_intents_reopen_without_deleted_media(tmp_path):
    from tests.test_retention_authorization import recovery_fixture

    root, parts, _, audit, run, _, _ = recovery_fixture(tmp_path)
    (parts / "connections.jsonl").write_text(json.dumps(
        {"connection": 1, "started_at": 1000, "ended_at": 1005}) + "\n")
    run()
    assert not parts.exists()
    with RetentionAudit(root, audit):
        pass


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


def _paired_intent(root, indices=(1,), *, hashes=True):
    """Build a historical order with canonical recovery evidence and parts."""
    fields = intent_fields(root)
    session_id = fields["session_id"]
    media = [str(Path("alpha.parts") /
                 f".tikrec-writer-crash-{session_id}-part-{index:04d}.evidence")
             for index in indices]
    media += [str(Path("alpha.parts") / f"part-{index:04d}.flv")
              for index in sorted({1, *indices})]
    order = sorted(media) + list(ORDER[1:])
    prototype = fields["artifacts"][0]
    artifacts = []
    for index, path in enumerate(order):
        item = copy.deepcopy(prototype)
        item["relative_path"] = path
        item["inode"] = index + 10
        if path == "alpha.parts":
            item["kind"], item["mode"] = "directory", 0o40777
        artifacts.append(item)
    fields["order"], fields["artifacts"] = order, artifacts
    if hashes:
        proof = [path for path in order if path in media]
        fields["recovery_byte_hashes"] = {path: "a" * 64 for path in proof}
    return fields


@pytest.mark.parametrize("indices,hashes", [((1,), True), ((1, 2), True),
                                           ((1,), False)])
def test_valid_recovery_pair_history_is_self_contained(tmp_path, indices, hashes):
    fields = _paired_intent(tmp_path, indices, hashes=hashes)
    AuditHistory(tmp_path).accept(event("intent", new_operation(), **fields))


@pytest.mark.parametrize("fault", ["orphan", "wrong_index", "duplicate_spelling",
                                   "partial_hashes", "wrong_hash_path"])
def test_impossible_recovery_pair_history_is_rejected(tmp_path, fault):
    fields = _paired_intent(tmp_path, (1, 2))
    order = fields["order"]
    evidence = next(path for path in order if "part-0002.evidence" in path)
    part = str(Path("alpha.parts") / "part-0002.flv")
    if fault == "orphan":
        position = order.index(part)
        order.pop(position)
        fields["artifacts"].pop(position)
        fields["recovery_byte_hashes"].pop(part)
    elif fault == "wrong_index":
        position = order.index(evidence)
        wrong = evidence.replace("part-0002.evidence", "part-0003.evidence")
        order[position] = wrong
        fields["artifacts"][position]["relative_path"] = wrong
        fields["recovery_byte_hashes"][wrong] = fields["recovery_byte_hashes"].pop(evidence)
    elif fault == "duplicate_spelling":
        position = order.index(evidence)
        wrong = evidence.replace("part-0002.evidence", "part-00002.evidence")
        order[position] = wrong
        fields["artifacts"][position]["relative_path"] = wrong
        fields["recovery_byte_hashes"][wrong] = fields["recovery_byte_hashes"].pop(evidence)
    elif fault == "partial_hashes":
        fields["recovery_byte_hashes"].pop(part)
    else:
        fields["recovery_byte_hashes"][str(Path("alpha.parts") / "session.json")] = "a" * 64
    with pytest.raises(ValueError):
        AuditHistory(tmp_path).accept(event("intent", new_operation(), **fields))


def test_new_artifact_hash_map_requires_every_file_and_matching_recovery(tmp_path):
    fields = _paired_intent(tmp_path)
    fields["artifact_byte_hashes"] = {
        path: "a" * 64 for path, item in zip(fields["order"], fields["artifacts"])
        if item["kind"] == "file"}
    AuditHistory(tmp_path).accept(event("intent", new_operation(), **fields))
    fields["artifact_byte_hashes"].pop(str(Path("alpha.parts") / "session.json"))
    with pytest.raises(ValueError, match="byte proof"):
        AuditHistory(tmp_path).accept(event("intent", new_operation(), **fields))


def test_new_artifact_hash_map_must_match_control_proof(tmp_path):
    fields = _paired_intent(tmp_path)
    fields["artifact_byte_hashes"] = {
        path: "a" * 64 for path, item in zip(fields["order"], fields["artifacts"])
        if item["kind"] == "file"}
    fields["target_controls"] = {"session.json": "b" * 64}
    with pytest.raises(ValueError, match="control byte proofs"):
        AuditHistory(tmp_path).accept(event("intent", new_operation(), **fields))


@pytest.mark.skipif(os.name != "nt", reason="Windows separator aliases")
@pytest.mark.parametrize("replacement", ["alpha.parts/part-0001.flv",
                                            "alpha.parts\\..\\part-0001.flv"])
def test_windows_separator_and_traversal_aliases_are_rejected(tmp_path, replacement):
    fields = intent_fields(tmp_path)
    fields["order"][0] = replacement
    fields["artifacts"][0]["relative_path"] = replacement
    with pytest.raises(ValueError):
        AuditHistory(tmp_path).accept(event("intent", new_operation(), **fields))
