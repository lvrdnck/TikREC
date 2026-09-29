"""Public retention results when operation and cleanup faults coincide."""

import argparse
import os
from contextlib import contextmanager
from io import StringIO

import pytest

from tests.test_retention_execute import events, fixture
from tests.test_retention_plan import NOW, inspect
from tikrec.lifecycle_lock import LifecycleLease
from tikrec.retention_audit import RetentionAudit
from tikrec.retention_cli import run_retention_command
from tikrec.retention_windows import HeldArtifact


def _invoke(case, stderr=None):
    """Call the public command against one disposable synthetic session."""
    root, _, session_id, config, jobs, audit, _ = case
    arguments = argparse.Namespace(
        config_path=str(config.path), retention_action="delete",
        session_id=session_id, root=str(root), confirm=session_id)
    stderr = stderr if stderr is not None else StringIO()
    code = run_retention_command(
        arguments, StringIO(), stderr, StringIO(), clock=lambda: NOW,
        media_inspector=inspect, job_paths=jobs, audit_path=audit)
    return code, stderr.getvalue()


def _fail_before_mutation(monkeypatch, fail_at, failure):
    """Inject a primary fault at a selected artifact without changing execution."""
    import tikrec.retention_delete_cli as cli

    original = cli.execute_retention
    seen = []

    def injected(*args, **kwargs):
        def before(path):
            if len(seen) == fail_at:
                raise failure("original execution fault")
            seen.append(path)
        return original(*args, before_mutation=before, **kwargs)

    monkeypatch.setattr(cli, "execute_retention", injected)


def _fail_cleanup(monkeypatch, owner, message="secondary cleanup fault"):
    """Raise after the real audit or lifecycle handle has been released."""
    original = owner.__exit__

    def fault_after_close(self, *exc):
        original(self, *exc)
        raise OSError(message)

    monkeypatch.setattr(owner, "__exit__", fault_after_close)


@pytest.mark.skipif(os.name != "nt", reason="Windows exact-object deletion only")
@pytest.mark.parametrize("fail_at,state", [(0, "FAILED"), (1, "PARTIAL")])
@pytest.mark.parametrize("owner", [RetentionAudit, LifecycleLease])
def test_primary_oserror_survives_cleanup_fault(tmp_path, monkeypatch,
                                                fail_at, state, owner):
    case = fixture(tmp_path)
    root, parts, _, _, _, audit, _ = case
    _fail_before_mutation(monkeypatch, fail_at, OSError)
    _fail_cleanup(monkeypatch, owner)

    code, err = _invoke(case)
    records = events(audit)
    assert code == 3 and f"{state}:" in err
    assert "reason=original execution fault" in err
    assert "Cleanup error: OSError: secondary cleanup fault" in err
    assert f"Operation ID: {records[0]['operation_id']}" in err
    assert f"Audit: {audit}" in err
    assert [event["event"] for event in records][-1] == "failed"
    assert parts.exists() and (root / "alpha.mp4").exists()
    assert sum(event["event"] == "deleted" for event in records) == fail_at


@pytest.mark.skipif(os.name != "nt", reason="Windows exact-object deletion only")
def test_primary_interrupt_survives_lifecycle_cleanup_fault(tmp_path, monkeypatch):
    case = fixture(tmp_path)
    _, parts, _, _, _, audit, _ = case
    _fail_before_mutation(monkeypatch, 0, KeyboardInterrupt)
    _fail_cleanup(monkeypatch, LifecycleLease)

    code, err = _invoke(case)
    assert code == 3 and "FAILED:" in err
    assert "reason=original execution fault" in err
    assert "Cleanup error: OSError: secondary cleanup fault" in err
    assert f"Operation ID: {events(audit)[0]['operation_id']}" in err
    assert f"Audit: {audit}" in err and parts.exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows exact-object deletion only")
@pytest.mark.parametrize("fail_at,state", [(0, "FAILED"), (1, "PARTIAL")])
def test_system_exit_during_attempt_has_incomplete_result(tmp_path, monkeypatch,
                                                          fail_at, state):
    case = fixture(tmp_path)
    root, parts, _, _, _, audit, _ = case
    original = RetentionAudit.append
    attempts = 0

    def fault_on_attempt(self, event, operation_id, **fields):
        nonlocal attempts
        if event == "attempt":
            if attempts == fail_at:
                raise SystemExit(17)
            attempts += 1
        return original(self, event, operation_id, **fields)

    monkeypatch.setattr(RetentionAudit, "append", fault_on_attempt)
    code, err = _invoke(case)
    records = events(audit)
    assert code == 3 and f"{state}:" in err and "reason=17" in err
    assert f"Operation ID: {records[0]['operation_id']}" in err
    assert f"Audit: {audit}" in err
    assert [event["event"] for event in records][-1] == "failed"
    assert sum(event["event"] == "deleted" for event in records) == fail_at
    assert parts.exists() and (root / "alpha.mp4").exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows exact-object deletion only")
@pytest.mark.parametrize("channel_fault", ["write", "flush"])
@pytest.mark.parametrize("owner", [RetentionAudit, LifecycleLease])
def test_combined_fault_and_broken_diagnostic_stays_exit_three(
        tmp_path, monkeypatch, channel_fault, owner):
    case = fixture(tmp_path)
    _fail_before_mutation(monkeypatch, 0, OSError)
    _fail_cleanup(monkeypatch, owner)

    class BrokenDiagnostic(StringIO):
        def write(self, value):
            if channel_fault == "write":
                raise OSError("broken stderr write")
            return super().write(value)

        def flush(self):
            if channel_fault == "flush":
                raise OSError("broken stderr flush")
            return super().flush()

    code, err = _invoke(case, BrokenDiagnostic())
    assert code == 3 and events(case[5])[-1]["event"] == "failed"
    if channel_fault == "flush":
        assert "reason=original execution fault" in err
        assert "Cleanup error: OSError: secondary cleanup fault" in err


@pytest.mark.skipif(os.name != "nt", reason="Windows exact-object deletion only")
@pytest.mark.parametrize("failure,code", [(OSError, 1), (KeyboardInterrupt, 130)])
def test_pre_sync_fault_keeps_pre_intent_exit_despite_cleanup(
        tmp_path, monkeypatch, failure, code):
    case = fixture(tmp_path)
    original = RetentionAudit.append

    def fault_before_sync(self, event, operation_id, **fields):
        if event == "intent":
            raise failure("original pre-sync fault")
        return original(self, event, operation_id, **fields)

    monkeypatch.setattr(RetentionAudit, "append", fault_before_sync)
    _fail_cleanup(monkeypatch, RetentionAudit)
    result, err = _invoke(case)
    assert result == code and not events(case[5])
    if code == 1:
        assert "REFUSED:" in err and "original pre-sync fault" in err
    else:
        assert "interrupted before intent" in err and "FAILED" not in err
    assert case[1].exists() and (case[0] / "alpha.mp4").exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows exact-object deletion only")
def test_unsynced_completion_and_cleanup_fault_stay_partial(tmp_path, monkeypatch):
    case = fixture(tmp_path)
    root, parts, _, _, _, audit, _ = case
    original = RetentionAudit.append

    def fault_on_completion(self, event, operation_id, **fields):
        if event == "completed":
            raise OSError("original completion persistence fault")
        return original(self, event, operation_id, **fields)

    monkeypatch.setattr(RetentionAudit, "append", fault_on_completion)
    _fail_cleanup(monkeypatch, RetentionAudit)
    code, err = _invoke(case)
    records = events(audit)
    assert code == 3 and "PARTIAL:" in err and "COMPLETE:" not in err
    assert "reason=original completion persistence fault" in err
    assert "Cleanup error: OSError: secondary cleanup fault" in err
    assert f"Operation ID: {records[0]['operation_id']}" in err
    assert f"Audit: {audit}" in err and records[-1]["event"] == "deleted"
    assert not parts.exists() and not (root / "alpha.mp4").exists()


def _fail_held_exit(monkeypatch, message="later held cleanup fault"):
    """Close the disposable Windows handle, then inject a cleanup exception."""
    original = HeldArtifact.__exit__

    def fail_after_close(self, *exc):
        original(self, *exc)
        raise OSError(message)

    monkeypatch.setattr(HeldArtifact, "__exit__", fail_after_close)


@pytest.mark.skipif(os.name != "nt", reason="Windows exact-object deletion only")
@pytest.mark.parametrize("primary_type", [OSError, KeyboardInterrupt, SystemExit])
def test_first_proof_fault_survives_held_cleanup(tmp_path, monkeypatch, primary_type):
    case = fixture(tmp_path)
    root, parts, _, _, _, audit, _ = case

    def first_proof_fault(self, _digest):
        raise primary_type("first proof fault")

    monkeypatch.setattr(HeldArtifact, "prove", first_proof_fault)
    _fail_held_exit(monkeypatch)
    code, err = _invoke(case)
    records = events(audit)
    assert code == 3 and "PARTIAL:" in err
    assert "reason=first proof fault" in err
    assert "Inner cleanup error: OSError: later held cleanup fault" in err
    assert records[-1]["event"] == "failed"
    assert records[-1]["error_type"] == primary_type.__name__
    assert f"Operation ID: {records[0]['operation_id']}" in err
    assert f"Audit: {audit}" in err
    assert (root / records[0]["quarantine_order"][0]).exists()
    assert not (parts / "part-0001.flv").exists()
    assert (root / "alpha.mp4").exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows exact-object deletion only")
def test_first_delete_interrupt_survives_held_and_outer_cleanup(tmp_path, monkeypatch):
    case = fixture(tmp_path)
    _, _, _, _, _, audit, _ = case

    def first_delete_fault(self):
        raise KeyboardInterrupt("first delete fault")

    monkeypatch.setattr(HeldArtifact, "delete", first_delete_fault)
    _fail_held_exit(monkeypatch)
    _fail_cleanup(monkeypatch, RetentionAudit, "later audit cleanup fault")
    code, err = _invoke(case)
    records = events(audit)
    assert code == 3 and "PARTIAL:" in err
    assert "reason=first delete fault" in err
    assert "Inner cleanup error: OSError: later held cleanup fault" in err
    assert "Cleanup error: OSError: later audit cleanup fault" in err
    assert records[-1]["error_type"] == "KeyboardInterrupt"
    assert f"Operation ID: {records[0]['operation_id']}" in err
    assert f"Audit: {audit}" in err


@pytest.mark.skipif(os.name != "nt", reason="Windows exact-object deletion only")
def test_first_delete_fault_survives_policy_cleanup(tmp_path, monkeypatch):
    case = fixture(tmp_path)
    _, _, _, _, _, audit, _ = case
    import tikrec.retention_execute as executor
    original_policy = executor.policy_lock

    @contextmanager
    def policy_with_cleanup_fault(*args, **kwargs):
        with original_policy(*args, **kwargs) as lease:
            try:
                yield lease
            finally:
                raise OSError("later policy cleanup fault")

    def first_delete_fault(self):
        raise SystemExit("first delete fault")

    monkeypatch.setattr(executor, "policy_lock", policy_with_cleanup_fault)
    monkeypatch.setattr(HeldArtifact, "delete", first_delete_fault)
    _fail_held_exit(monkeypatch)
    code, err = _invoke(case)
    records = events(audit)
    assert code == 3 and "PARTIAL:" in err
    assert "reason=first delete fault" in err
    assert "Inner cleanup error: OSError: later policy cleanup fault" in err
    assert "Inner cleanup error: OSError: later held cleanup fault" in err
    assert err.index("later policy cleanup fault") < err.index("later held cleanup fault")
    assert records[-1]["error_type"] == "SystemExit"


@pytest.mark.skipif(os.name != "nt", reason="Windows exact-object deletion only")
@pytest.mark.parametrize("channel_fault", ["none", "write", "flush"])
def test_inner_fault_with_failed_event_and_broken_diagnostic(
        tmp_path, monkeypatch, channel_fault):
    case = fixture(tmp_path)
    _, _, _, _, _, audit, _ = case
    original_append = RetentionAudit.append

    def first_proof_fault(self, _digest):
        raise SystemExit("first proof fault")

    def failed_event_fault(self, event, operation_id, **fields):
        original_append(self, event, operation_id, **fields)
        if event == "failed":
            raise OSError("later failed-event persistence fault")

    class Diagnostic(StringIO):
        def write(self, value):
            if channel_fault == "write":
                raise OSError("broken stderr write")
            return super().write(value)

        def flush(self):
            if channel_fault == "flush":
                raise OSError("broken stderr flush")
            return super().flush()

    monkeypatch.setattr(HeldArtifact, "prove", first_proof_fault)
    _fail_held_exit(monkeypatch)
    monkeypatch.setattr(RetentionAudit, "append", failed_event_fault)
    code, err = _invoke(case, Diagnostic())
    records = events(audit)
    assert code == 3
    assert [record["event"] for record in records] == ["intent", "attempt", "failed"]
    assert records[-1]["error_type"] == "SystemExit"
    if channel_fault != "write":
        assert "PARTIAL:" in err and "reason=first proof fault" in err
        assert "Inner cleanup error: OSError: later held cleanup fault" in err
        assert "Audit state may be incomplete" in err
        assert f"Operation ID: {records[0]['operation_id']}" in err
        assert f"Audit: {audit}" in err


@pytest.mark.skipif(os.name != "nt", reason="Windows exact-object deletion only")
def test_held_cleanup_is_primary_when_body_succeeds(tmp_path, monkeypatch):
    case = fixture(tmp_path)
    _, _, _, _, _, audit, _ = case
    _fail_held_exit(monkeypatch, "first held cleanup fault")
    code, err = _invoke(case)
    records = events(audit)
    assert code == 3 and "PARTIAL:" in err
    assert "reason=first held cleanup fault" in err
    assert "Inner cleanup error:" not in err
    assert records[-1]["error_type"] == "OSError"


@pytest.mark.skipif(os.name != "nt", reason="Windows exact-object deletion only")
def test_enter_identity_fault_survives_its_own_close_fault(tmp_path, monkeypatch):
    case = fixture(tmp_path)
    root, parts, _, _, _, audit, _ = case
    original_close = HeldArtifact.close

    def first_identity_fault(self):
        raise SystemExit("first opened-handle identity fault")

    def later_close_fault(self):
        original_close(self)
        raise OSError("later enter cleanup fault")

    monkeypatch.setattr(HeldArtifact, "_identity", first_identity_fault)
    monkeypatch.setattr(HeldArtifact, "close", later_close_fault)
    code, err = _invoke(case)
    records = events(audit)
    assert code == 3 and "PARTIAL:" in err
    assert "reason=first opened-handle identity fault" in err
    assert "Inner cleanup error: OSError: later enter cleanup fault" in err
    assert records[-1]["error_type"] == "SystemExit"
    assert (parts / "part-0001.flv").exists()
    assert (root / "alpha.mp4").exists()
