"""Public retention results through audit entry and lifecycle cleanup faults."""

import os
from io import StringIO

import pytest

import tikrec.lifecycle_lock as lifecycle_module
import tikrec.retention_audit as audit_module
from tests.test_lifecycle_lock import _CloseFault
from tests.test_retention_execute import events, fixture
from tests.test_retention_primary_result import _fail_before_mutation, _invoke
from tests.test_retention_policy_teardown import _fail_policy_teardown
from tests.test_retention_inner_result import _fail_held_exit
from tikrec.lifecycle_lock import LifecycleLease
from tikrec.retention_audit import RetentionAudit
from tikrec.retention_windows import HeldArtifact


def _fault_lifecycle_cleanup(monkeypatch):
    """Make real unlock and close succeed, then raise distinct fault types."""
    real_init, real_unlock = LifecycleLease.__init__, lifecycle_module._unlock

    def wrapping_init(self, *args, **kwargs):
        real_init(self, *args, **kwargs)
        self.handle = _CloseFault(self.handle)

    def unlock_then_fault(*args):
        real_unlock(*args)
        raise KeyboardInterrupt("first lifecycle unlock fault")

    monkeypatch.setattr(LifecycleLease, "__init__", wrapping_init)
    monkeypatch.setattr(lifecycle_module, "_unlock", unlock_then_fault)


class _Diagnostic(StringIO):
    """Keep a visible buffer even when the requested diagnostic step fails."""

    def __init__(self, failure):
        super().__init__()
        self.failure = failure

    def write(self, value):
        if self.failure == "write":
            raise OSError("broken stderr write")
        return super().write(value)

    def flush(self):
        if self.failure == "flush":
            raise OSError("broken stderr flush")
        return super().flush()


@pytest.mark.skipif(os.name != "nt", reason="Windows exact-object deletion only")
@pytest.mark.parametrize("first,expected", [(ValueError, 1), (KeyboardInterrupt, 130)])
def test_public_audit_entry_preserves_first_preintent_fault(
        tmp_path, monkeypatch, first, expected):
    case = fixture(tmp_path)
    root, parts, _, _, _, audit, _ = case
    real_enter, real_fdopen = RetentionAudit.__enter__, audit_module.os.fdopen

    def entering(self):
        with monkeypatch.context() as scoped:
            scoped.setattr(audit_module.os, "fdopen",
                           lambda *a, **kw: _CloseFault(real_fdopen(*a, **kw)))
            return real_enter(self)

    def first_validation(*_args):
        raise first("first audit entry fault")

    monkeypatch.setattr(RetentionAudit, "__enter__", entering)
    monkeypatch.setattr(audit_module, "_validate_history", first_validation)
    code, err = _invoke(case)
    assert code == expected and "first audit entry fault" in err
    assert "second handle close fault" in err
    assert "Operation ID:" not in err and audit.read_bytes() == b""
    assert parts.exists() and (root / "alpha.mp4").exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows exact-object deletion only")
@pytest.mark.parametrize("stage", ["complete", "incomplete"])
@pytest.mark.parametrize("diagnostic", ["none", "write", "flush"])
def test_lifecycle_first_fault_and_registry_across_public_results(
        tmp_path, monkeypatch, stage, diagnostic):
    case = fixture(tmp_path)
    root, parts, _, _, _, audit, _ = case
    if stage == "incomplete":
        _fail_before_mutation(monkeypatch, 0, OSError)
    _fault_lifecycle_cleanup(monkeypatch)
    code, err = _invoke(case, _Diagnostic(diagnostic))
    records = events(audit)
    assert code == (0 if stage == "complete" else 3)
    assert case[0].__str__().casefold() not in lifecycle_module._registry
    assert records[0]["operation_id"] and records[0]["event"] == "intent"
    if stage == "complete":
        assert records[-1]["event"] == "completed"
        assert not parts.exists() and not (root / "alpha.mp4").exists()
    else:
        assert records[-1]["error_type"] == "OSError"
        assert parts.exists() and (root / "alpha.mp4").exists()
    if diagnostic != "write":
        assert "first lifecycle unlock fault" in err
        assert "second handle close fault" in err
        assert err.index("first lifecycle unlock fault") < err.index(
            "second handle close fault")
        assert f"Operation ID: {records[0]['operation_id']}" in err
        assert f"Audit: {audit}" in err
        if stage == "complete":
            assert "COMPLETE:" in err and "PARTIAL:" not in err
        else:
            assert "FAILED:" in err and "reason=original execution fault" in err


@pytest.mark.skipif(os.name != "nt", reason="Windows exact-object deletion only")
def test_completed_audit_fault_precedes_both_lifecycle_cleanup_faults(
        tmp_path, monkeypatch):
    case = fixture(tmp_path)
    _, _, _, _, _, audit, _ = case
    real_exit = RetentionAudit.__exit__

    def first_audit_close(self, *exc):
        real_exit(self, *exc)
        raise OSError("first audit close fault")

    monkeypatch.setattr(RetentionAudit, "__exit__", first_audit_close)
    _fault_lifecycle_cleanup(monkeypatch)
    code, err = _invoke(case, _Diagnostic("flush"))
    records = events(audit)
    assert code == 0 and records[-1]["event"] == "completed"
    assert "COMPLETE:" in err and "Post-completion error: OSError: first audit close fault" in err
    assert err.index("first audit close fault") < err.index(
        "first lifecycle unlock fault") < err.index("second handle close fault")
    assert f"Operation ID: {records[0]['operation_id']}" in err
    assert f"Audit: {audit}" in err


@pytest.mark.skipif(os.name != "nt", reason="Windows exact-object deletion only")
def test_inner_and_outer_cleanup_keep_first_operation_and_all_later_faults(
        tmp_path, monkeypatch):
    case = fixture(tmp_path)
    _, _, _, _, _, audit, _ = case
    real_append, real_exit = RetentionAudit.append, RetentionAudit.__exit__

    def first_delete(self):
        raise SystemExit("first artifact delete fault")

    def failed_event_fault(self, event, operation_id, **fields):
        real_append(self, event, operation_id, **fields)
        if event == "failed":
            raise OSError("later failed-event append fault")

    def audit_exit_fault(self, *exc):
        real_exit(self, *exc)
        raise OSError("later audit close fault")

    with monkeypatch.context() as scoped:
        scoped.setattr(HeldArtifact, "delete", first_delete)
        _fail_policy_teardown(scoped)
        _fail_held_exit(scoped, "later held close fault")
        scoped.setattr(RetentionAudit, "append", failed_event_fault)
        scoped.setattr(RetentionAudit, "__exit__", audit_exit_fault)
        _fault_lifecycle_cleanup(scoped)
        code, err = _invoke(case, _Diagnostic("flush"))
    assert code == 3 and "PARTIAL:" in err
    assert "reason=first artifact delete fault" in err
    assert events(audit)[-1]["error_type"] == "SystemExit"
    assert err.index("first policy close fault") < err.index(
        "second policy notification fault") < err.index(
            "later held close fault") < err.index(
                "later audit close fault") < err.index(
                    "first lifecycle unlock fault") < err.index(
                        "second handle close fault")
