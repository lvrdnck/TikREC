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
    assert "Secondary cleanup error:" not in err
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


@pytest.mark.skipif(os.name != "nt", reason="Windows exact-object deletion only")
@pytest.mark.parametrize("primary_type", [KeyboardInterrupt, SystemExit, RuntimeError])
def test_first_fault_after_completed_sync_survives_audit_cleanup(
        tmp_path, monkeypatch, primary_type):
    case = fixture(tmp_path)
    root, parts, _, _, _, audit, _ = case
    original_append = RetentionAudit.append
    original_exit = RetentionAudit.__exit__

    def fault_after_completed(self, event, operation_id, **fields):
        original_append(self, event, operation_id, **fields)
        if event == "completed":
            raise primary_type("first post-completion fault")

    def fault_after_close(self, *exc):
        original_exit(self, *exc)
        raise OSError("second audit cleanup fault")

    monkeypatch.setattr(RetentionAudit, "append", fault_after_completed)
    monkeypatch.setattr(RetentionAudit, "__exit__", fault_after_close)
    code, _, err = _invoke(case)
    records = events(audit)
    assert code == 0 and records[-1]["event"] == "completed"
    assert not parts.exists() and not (root / "alpha.mp4").exists()
    assert f"Post-completion error: {primary_type.__name__}: first post-completion fault" in err
    assert "Secondary cleanup error: OSError: second audit cleanup fault" in err
    assert f"Operation ID: {records[0]['operation_id']}" in err
    assert f"Audit: {audit}" in err
    assert "PARTIAL:" not in err and "FAILED:" not in err


@pytest.mark.skipif(os.name != "nt", reason="Windows exact-object deletion only")
@pytest.mark.parametrize("later_type", [OSError, KeyboardInterrupt, SystemExit])
def test_first_audit_cleanup_fault_survives_lifecycle_cleanup(
        tmp_path, monkeypatch, later_type):
    case = fixture(tmp_path)
    root, parts, _, _, _, audit, _ = case
    original_audit_exit = RetentionAudit.__exit__
    original_lease_exit = LifecycleLease.__exit__

    def fault_after_audit_close(self, *exc):
        original_audit_exit(self, *exc)
        raise OSError("first audit cleanup fault")

    def fault_after_lease_close(self, *exc):
        original_lease_exit(self, *exc)
        raise later_type("second lifecycle cleanup fault")

    monkeypatch.setattr(RetentionAudit, "__exit__", fault_after_audit_close)
    monkeypatch.setattr(LifecycleLease, "__exit__", fault_after_lease_close)
    code, _, err = _invoke(case)
    records = events(audit)
    assert code == 0 and records[-1]["event"] == "completed"
    assert not parts.exists() and not (root / "alpha.mp4").exists()
    assert "Post-completion error: OSError: first audit cleanup fault" in err
    assert (f"Secondary cleanup error: {later_type.__name__}: "
            "second lifecycle cleanup fault") in err
    assert f"Operation ID: {records[0]['operation_id']}" in err
    assert f"Audit: {audit}" in err


@pytest.mark.skipif(os.name != "nt", reason="Windows exact-object deletion only")
@pytest.mark.parametrize("boundary", ["post_completed", "two_cleanups"])
@pytest.mark.parametrize("channel_fault", ["write", "flush"])
def test_combined_completed_faults_keep_zero_with_broken_stderr(
        tmp_path, monkeypatch, boundary, channel_fault):
    case = fixture(tmp_path)
    root, parts, _, _, _, audit, _ = case
    original_audit_exit = RetentionAudit.__exit__

    def fault_after_audit_close(self, *exc):
        original_audit_exit(self, *exc)
        raise OSError("first audit cleanup fault" if boundary == "two_cleanups"
                      else "second audit cleanup fault")

    monkeypatch.setattr(RetentionAudit, "__exit__", fault_after_audit_close)
    if boundary == "post_completed":
        original_append = RetentionAudit.append

        def fault_after_completed(self, event, operation_id, **fields):
            original_append(self, event, operation_id, **fields)
            if event == "completed":
                raise KeyboardInterrupt("first post-completion fault")

        monkeypatch.setattr(RetentionAudit, "append", fault_after_completed)
    else:
        original_lease_exit = LifecycleLease.__exit__

        def fault_after_lease_close(self, *exc):
            original_lease_exit(self, *exc)
            raise OSError("second lifecycle cleanup fault")

        monkeypatch.setattr(LifecycleLease, "__exit__", fault_after_lease_close)

    class BrokenDiagnostic(StringIO):
        def write(self, value):
            if channel_fault == "write":
                raise OSError("broken stderr write")
            return super().write(value)

        def flush(self):
            if channel_fault == "flush":
                raise OSError("broken stderr flush")
            return super().flush()

    code, _, err = _invoke(case, BrokenDiagnostic())
    assert code == 0 and events(audit)[-1]["event"] == "completed"
    assert not parts.exists() and not (root / "alpha.mp4").exists()
    if channel_fault == "flush":
        assert "COMPLETE:" in err and "Secondary cleanup error:" in err


def _post_completion_faults(monkeypatch, scenario):
    """Inject the issue #44 fault order after genuine completed persistence."""
    audit_exit = RetentionAudit.__exit__

    def fail_audit_close(self, *exc):
        audit_exit(self, *exc)
        message = ("secondary audit close fault" if scenario == "append_then_audit"
                   else "first audit cleanup fault")
        raise OSError(message)

    monkeypatch.setattr(RetentionAudit, "__exit__", fail_audit_close)
    if scenario == "append_then_audit":
        append = RetentionAudit.append

        def interrupt_after_completed(self, event, operation_id, **fields):
            append(self, event, operation_id, **fields)
            if event == "completed":
                raise KeyboardInterrupt("primary after-completed interruption")

        monkeypatch.setattr(RetentionAudit, "append", interrupt_after_completed)
    else:
        lifecycle_exit = LifecycleLease.__exit__

        def fail_lifecycle_close(self, *exc):
            lifecycle_exit(self, *exc)
            raise OSError("second lifecycle cleanup fault")

        monkeypatch.setattr(LifecycleLease, "__exit__", fail_lifecycle_close)


@pytest.mark.skipif(os.name != "nt", reason="Windows exact-object deletion only")
@pytest.mark.parametrize("scenario,primary,secondary", [
    ("append_then_audit", "KeyboardInterrupt: primary after-completed interruption",
     "OSError: secondary audit close fault"),
    ("audit_then_lifecycle", "OSError: first audit cleanup fault",
     "OSError: second lifecycle cleanup fault"),
])
@pytest.mark.parametrize("channel_fault", [None, "write", "flush"])
def test_first_post_completion_fault_survives_later_cleanup(
        tmp_path, monkeypatch, scenario, primary, secondary, channel_fault):
    case = fixture(tmp_path)
    root, parts, _, _, _, audit, _ = case
    _post_completion_faults(monkeypatch, scenario)

    class Diagnostic(StringIO):
        def write(self, value):
            if channel_fault == "write":
                raise OSError("broken stderr write")
            return super().write(value)

        def flush(self):
            if channel_fault == "flush":
                raise OSError("broken stderr flush")
            return super().flush()

    code, _, err = _invoke(case, Diagnostic())
    records = events(audit)
    assert code == 0 and records[-1]["event"] == "completed"
    assert not parts.exists() and not (root / "alpha.mp4").exists()
    if channel_fault != "write":
        assert "COMPLETE" in err and "PARTIAL" not in err and "FAILED" not in err
        assert f"Post-completion error: {primary}" in err
        assert f"Secondary cleanup error: {secondary}" in err
        assert err.index(primary) < err.index(secondary)
        assert f"Operation ID: {records[0]['operation_id']}" in err
        assert f"Audit: {audit}" in err
