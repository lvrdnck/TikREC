"""Public retention outcomes at the durable audit-intent boundary."""

import argparse
import os
from io import StringIO

import pytest

from tests.test_retention_delete_cli import call
from tests.test_retention_execute import events, fixture
from tests.test_retention_plan import NOW, inspect
from tikrec.retention_audit import RetentionAudit
from tikrec.retention_cli import run_retention_command


def _call_with_diagnostics(case, stderr):
    """Run the public command with a disposable session and chosen stderr."""
    root, _, session_id, config, jobs, audit, _ = case
    arguments = argparse.Namespace(
        config_path=str(config.path), retention_action="delete",
        session_id=session_id, root=str(root), confirm=session_id)
    return run_retention_command(
        arguments, StringIO(), stderr, StringIO(), clock=lambda: NOW,
        media_inspector=inspect, job_paths=jobs, audit_path=audit)


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
@pytest.mark.parametrize("failure", [OSError, KeyboardInterrupt])
def test_fault_after_real_intent_fsync_reports_uncertain_after_intent(
        tmp_path, monkeypatch, failure):
    case = fixture(tmp_path)
    root, parts, session_id, _, _, audit, _ = case
    import tikrec.retention_audit as audit_module

    original_append = RetentionAudit.append
    original_sync = audit_module.os.fsync

    def fault_after_real_sync(descriptor):
        original_sync(descriptor)
        raise failure("synthetic fault after successful OS fsync")

    def fault_during_intent(self, event, operation_id, **fields):
        if event == "intent":
            with monkeypatch.context() as patch:
                patch.setattr(audit_module.os, "fsync", fault_after_real_sync)
                return original_append(self, event, operation_id, **fields)
        return original_append(self, event, operation_id, **fields)

    monkeypatch.setattr(RetentionAudit, "append", fault_during_intent)
    code, _, err = call(case, confirm=session_id)
    records = events(audit)
    assert [record["event"] for record in records] == ["intent"]
    assert code == 3 and "FAILED" in err
    assert "synthetic fault after successful OS fsync" in err
    assert "Audit intent durability was not confirmed" in err
    assert f"Operation ID: {records[0]['operation_id']}" in err
    assert f"Audit: {audit}" in err
    assert "REFUSED" not in err and "interrupted before intent" not in err
    assert "No deletion operation was started" not in err
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
def test_failed_intent_fsync_keeps_durability_uncertain(tmp_path, monkeypatch):
    case = fixture(tmp_path)
    root, parts, session_id, _, _, audit, _ = case
    import tikrec.retention_audit as audit_module
    original = RetentionAudit.append

    def fail_sync(_descriptor):
        # A raised sync call does not prove the write was never persisted.
        raise OSError("synthetic intent fsync failure")

    def fault_during_append(self, event, operation_id, **fields):
        with monkeypatch.context() as patch:
            patch.setattr(audit_module.os, "fsync", fail_sync)
            return original(self, event, operation_id, **fields)

    monkeypatch.setattr(RetentionAudit, "append", fault_during_append)
    code, _, err = call(case, confirm=session_id)
    assert code == 3 and "FAILED" in err
    assert "Audit intent durability was not confirmed" in err
    assert "synthetic intent fsync failure" in err
    assert "Operation ID:" in err and f"Audit: {audit}" in err
    assert "The audit record preserves" not in err
    assert "REFUSED" not in err and "No deletion operation was started" not in err
    assert parts.exists() and (root / "alpha.mp4").exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows retention deletion only")
@pytest.mark.parametrize("channel_fault", ["write", "flush"])
@pytest.mark.parametrize("failure", [OSError, KeyboardInterrupt])
def test_broken_after_intent_diagnostics_keep_exit_three(
        tmp_path, monkeypatch, channel_fault, failure):
    case = fixture(tmp_path)
    root, parts, _, _, _, audit, _ = case
    import tikrec.retention_delete_cli as cli

    original = cli.execute_retention

    def fail_after_intent(*args, **kwargs):
        def stop_before_removal(_path):
            raise OSError("original executor failure")
        return original(*args, before_mutation=stop_before_removal, **kwargs)

    class BrokenStderr(StringIO):
        def write(self, value):
            if channel_fault == "write":
                raise failure("synthetic diagnostic write failure")
            return super().write(value)

        def flush(self):
            if channel_fault == "flush":
                raise failure("synthetic diagnostic flush failure")
            return super().flush()

    monkeypatch.setattr(cli, "execute_retention", fail_after_intent)
    stderr = BrokenStderr()
    code = _call_with_diagnostics(case, stderr)
    assert code == 3
    records = events(audit)
    assert [record["event"] for record in records] == ["intent", "failed"]
    if channel_fault == "flush":
        assert "original executor failure" in stderr.getvalue()
        assert f"Operation ID: {records[0]['operation_id']}" in stderr.getvalue()
        assert f"Audit: {audit}" in stderr.getvalue()
    assert parts.exists() and (root / "alpha.mp4").exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows retention deletion only")
@pytest.mark.parametrize("failure", [OSError, KeyboardInterrupt])
def test_broken_pre_intent_diagnostics_keep_refusal(tmp_path, failure):
    case = fixture(tmp_path)
    root, parts, session_id, config, jobs, audit, _ = case
    arguments = argparse.Namespace(
        config_path=str(config.path), retention_action="delete",
        session_id=session_id, root=str(root), confirm="wrong")

    class BrokenStderr(StringIO):
        def write(self, _value):
            raise failure("synthetic diagnostic failure")

    code = run_retention_command(
        arguments, StringIO(), BrokenStderr(), StringIO(), clock=lambda: NOW,
        media_inspector=inspect, job_paths=jobs, audit_path=audit)
    assert code == 1 and not audit.exists()
    assert parts.exists() and (root / "alpha.mp4").exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows retention deletion only")
def test_broken_pre_intent_interrupt_diagnostics_keep_130(tmp_path, monkeypatch):
    case = fixture(tmp_path)
    root, parts, _, _, _, audit, _ = case
    import tikrec.retention_delete_cli as cli

    class BrokenStderr(StringIO):
        def write(self, _value):
            raise OSError("synthetic diagnostic failure")

    def interrupt_before_preview(*_args, **_kwargs):
        raise KeyboardInterrupt("original pre-intent interrupt")

    monkeypatch.setattr(cli, "prepare_preview", interrupt_before_preview)
    code = _call_with_diagnostics(case, BrokenStderr())
    assert code == 130 and not audit.exists()
    assert parts.exists() and (root / "alpha.mp4").exists()
