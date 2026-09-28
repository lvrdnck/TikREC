"""Public retention outcomes at the durable audit-intent boundary."""

import os

import pytest

from tests.test_retention_delete_cli import call
from tests.test_retention_execute import events, fixture
from tikrec.retention_audit import RetentionAudit


@pytest.mark.skipif(os.name != "nt", reason="Windows retention deletion only")
@pytest.mark.parametrize("interrupted", [False, True])
def test_post_sync_intent_fault_reports_failed(tmp_path, monkeypatch, interrupted):
    case = fixture(tmp_path)
    root, parts, session_id, _, _, audit, _ = case
    original = RetentionAudit.append
    cause = (KeyboardInterrupt("synthetic post-sync interrupt") if interrupted
             else OSError("synthetic post-sync failure"))

    def fault_after_sync(self, event, operation_id, **fields):
        original(self, event, operation_id, **fields)
        if event == "intent":
            raise cause

    monkeypatch.setattr(RetentionAudit, "append", fault_after_sync)
    code, out, err = call(case, confirm=session_id)
    records = events(audit)
    assert [record["event"] for record in records] == ["intent"]
    assert code == 3 and "FAILED" in err and str(cause) in err
    assert f"Operation ID: {records[0]['operation_id']}" in err
    assert f"Audit: {audit}" in err
    assert "REFUSED" not in err and "interrupted before intent" not in err
    assert "No deletion operation was started" not in err and "COMPLETE" not in out
    assert parts.exists() and (root / "alpha.mp4").exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows retention deletion only")
@pytest.mark.parametrize("interrupted,code", [(False, 1), (True, 130)])
def test_pre_sync_intent_fault_keeps_pre_intent_result(tmp_path, monkeypatch,
                                                       interrupted, code):
    case = fixture(tmp_path)
    root, parts, session_id, _, _, audit, _ = case

    def fault_before_sync(self, event, operation_id, **fields):
        assert event == "intent"
        if interrupted:
            raise KeyboardInterrupt("synthetic pre-sync interrupt")
        raise OSError("synthetic pre-sync failure")

    monkeypatch.setattr(RetentionAudit, "append", fault_before_sync)
    result, _, err = call(case, confirm=session_id)
    assert result == code
    assert ("interrupted before intent" if interrupted else "REFUSED") in err
    assert "FAILED" not in err and "Operation ID:" not in err
    assert audit.exists() and audit.read_bytes() == b""
    assert parts.exists() and (root / "alpha.mp4").exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows retention deletion only")
def test_failed_intent_fsync_does_not_imply_durability(tmp_path, monkeypatch):
    case = fixture(tmp_path)
    root, parts, session_id, _, _, _, _ = case
    import tikrec.retention_audit as audit_module
    original = RetentionAudit.append

    def fail_sync(_descriptor):
        raise OSError("synthetic intent fsync failure")

    def fault_during_append(self, event, operation_id, **fields):
        with monkeypatch.context() as patch:
            patch.setattr(audit_module.os, "fsync", fail_sync)
            return original(self, event, operation_id, **fields)

    monkeypatch.setattr(RetentionAudit, "append", fault_during_append)
    code, _, err = call(case, confirm=session_id)
    assert code == 1 and "REFUSED" in err
    assert "Audit intent durability was not confirmed" in err
    assert "FAILED" not in err and "Operation ID:" not in err
    assert parts.exists() and (root / "alpha.mp4").exists()
