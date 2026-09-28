"""Public retention outcomes around a proven completed audit event."""

import argparse
import os
from io import StringIO

import pytest

from tests.test_retention_execute import events, fixture
from tests.test_retention_plan import NOW, inspect
from tikrec.lifecycle_lock import LifecycleLease
from tikrec.retention_audit import RetentionAudit
from tikrec.retention_cli import run_retention_command


def _invoke(case, stderr=None):
    """Run public deletion with disposable media and a chosen diagnostic stream."""
    root, _, session_id, config, jobs, audit, _ = case
    arguments = argparse.Namespace(
        config_path=str(config.path), retention_action="delete",
        session_id=session_id, root=str(root), confirm=session_id)
    stdout = StringIO()
    stderr = stderr if stderr is not None else StringIO()
    code = run_retention_command(
        arguments, stdout, stderr, StringIO(), clock=lambda: NOW,
        media_inspector=inspect, job_paths=jobs, audit_path=audit)
    return code, stdout.getvalue(), stderr.getvalue()


@pytest.mark.skipif(os.name != "nt", reason="Windows exact-object deletion only")
@pytest.mark.parametrize("failure", [OSError, KeyboardInterrupt, RuntimeError, SystemExit])
@pytest.mark.parametrize("boundary,owner", [
    ("audit", RetentionAudit), ("lifecycle", LifecycleLease)])
def test_proven_completion_survives_executor_cleanup(
        tmp_path, monkeypatch, boundary, owner, failure):
    case = fixture(tmp_path)
    root, parts, session_id, _, _, audit, _ = case
    original_exit = owner.__exit__

    def fault_after_cleanup(self, *exc):
        original_exit(self, *exc)
        raise failure(f"synthetic {boundary} cleanup fault")

    monkeypatch.setattr(owner, "__exit__", fault_after_cleanup)
    code, out, err = _invoke(case)
    records = events(audit)
    assert code == 0 and records[-1]["event"] == "completed"
    assert not parts.exists() and not (root / "alpha.mp4").exists()
    assert "COMPLETE" in err and "PARTIAL" not in err and "FAILED" not in err
    assert f"{failure.__name__}: synthetic {boundary} cleanup fault" in err
    assert f"Operation ID: {records[0]['operation_id']}" in err
    assert f"Audit: {audit}" in err
    assert f"Session: {session_id}" in out


@pytest.mark.skipif(os.name != "nt", reason="Windows exact-object deletion only")
@pytest.mark.parametrize("channel_fault", ["write", "flush"])
def test_proven_completion_survives_broken_cleanup_diagnostic(
        tmp_path, monkeypatch, channel_fault):
    case = fixture(tmp_path)
    root, parts, _, _, _, audit, _ = case
    original_exit = RetentionAudit.__exit__

    def fault_after_close(self, *exc):
        original_exit(self, *exc)
        raise OSError("original cleanup fault")

    class BrokenDiagnostic(StringIO):
        def write(self, value):
            if channel_fault == "write":
                raise OSError("broken diagnostic write")
            return super().write(value)

        def flush(self):
            if channel_fault == "flush":
                raise OSError("broken diagnostic flush")
            return super().flush()

    monkeypatch.setattr(RetentionAudit, "__exit__", fault_after_close)
    code, _, err = _invoke(case, BrokenDiagnostic())
    assert code == 0 and events(audit)[-1]["event"] == "completed"
    assert not parts.exists() and not (root / "alpha.mp4").exists()
    if channel_fault == "flush":
        assert "COMPLETE" in err and "original cleanup fault" in err


@pytest.mark.skipif(os.name != "nt", reason="Windows exact-object deletion only")
@pytest.mark.parametrize("failure", [OSError, KeyboardInterrupt])
def test_interrupted_completed_sync_is_not_proven(tmp_path, monkeypatch, failure):
    case = fixture(tmp_path)
    root, parts, _, _, _, audit, _ = case
    import tikrec.retention_audit as audit_module

    original_append = RetentionAudit.append
    original_sync = audit_module.os.fsync

    def fault_after_os_sync(descriptor):
        original_sync(descriptor)
        raise failure("synthetic completed sync uncertainty")

    def fault_on_completed(self, event, operation_id, **fields):
        if event == "completed":
            with monkeypatch.context() as patch:
                patch.setattr(audit_module.os, "fsync", fault_after_os_sync)
                return original_append(self, event, operation_id, **fields)
        return original_append(self, event, operation_id, **fields)

    monkeypatch.setattr(RetentionAudit, "append", fault_on_completed)
    code, _, err = _invoke(case)
    # A visible completed line and absent artifacts do not prove that the
    # interrupted sync returned successfully to the caller.
    assert events(audit)[-1]["event"] == "completed"
    assert not parts.exists() and not (root / "alpha.mp4").exists()
    assert code == 3 and "PARTIAL" in err and "COMPLETE" not in err
    assert "synthetic completed sync uncertainty" in err
