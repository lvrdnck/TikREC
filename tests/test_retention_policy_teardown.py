"""Public retention results across nested policy and outer cleanup faults."""

import importlib
import os
from io import StringIO

import pytest

from tests.test_retention_execute import events, fixture
from tests.test_retention_primary_result import (
    _fail_before_mutation, _fail_cleanup, _invoke)
from tests.test_retention_inner_result import _fail_held_exit
from tikrec.lifecycle_lock import LifecycleLease
from tikrec.retention_audit import RetentionAudit
from tikrec.retention_windows import HeldArtifact

def _fail_policy_teardown(monkeypatch, first_type=OSError):
    """Fault once after the real descriptor close and condition notification."""
    module = importlib.import_module("tikrec.policy_lock")
    original_init = module.PolicyLease.__init__
    original_close = os.close
    original_condition = module._condition
    state = {"descriptor": None, "closed": False, "notified": False}

    def capture_descriptor(self, path, descriptor):
        state["descriptor"] = descriptor
        original_init(self, path, descriptor)

    def first_close_fault(descriptor):
        if descriptor == state["descriptor"] and not state["closed"]:
            state["closed"] = True
            original_close(descriptor)
            raise first_type("first policy close fault")
        return original_close(descriptor)

    class NotificationFault:
        def __enter__(self):
            return original_condition.__enter__()

        def __exit__(self, *exc):
            return original_condition.__exit__(*exc)

        def wait(self):
            return original_condition.wait()

        def notify_all(self):
            original_condition.notify_all()
            if not state["notified"]:
                state["notified"] = True
                raise SystemExit("second policy notification fault")

    monkeypatch.setattr(module.PolicyLease, "__init__", capture_descriptor)
    monkeypatch.setattr(module.os, "close", first_close_fault)
    monkeypatch.setattr(module, "_condition", NotificationFault())


@pytest.mark.skipif(os.name != "nt", reason="Windows exact-object deletion only")
@pytest.mark.parametrize("first_type", [OSError, KeyboardInterrupt])
def test_policy_teardown_first_fault_controls_failed_event(
        tmp_path, monkeypatch, first_type):
    case = fixture(tmp_path)
    root, parts, _, _, _, audit, _ = case
    with monkeypatch.context() as scoped:
        _fail_policy_teardown(scoped, first_type)
        code, err = _invoke(case)
    records = events(audit)
    assert code == 3 and "PARTIAL:" in err and "COMPLETE:" not in err
    assert f"reason=first policy close fault" in err
    assert "Inner cleanup error: SystemExit: second policy notification fault" in err
    assert records[-1]["event"] == "failed"
    assert records[-1]["error_type"] == first_type.__name__
    assert f"Operation ID: {records[0]['operation_id']}" in err
    assert f"Audit: {audit}" in err
    assert not (parts / "part-0001.flv").exists()
    assert (root / "alpha.mp4").exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows exact-object deletion only")
def test_artifact_fault_precedes_both_policy_teardown_faults(tmp_path, monkeypatch):
    case = fixture(tmp_path)
    _, _, _, _, _, audit, _ = case

    def first_delete_fault(self):
        raise SystemExit("first artifact delete fault")

    with monkeypatch.context() as scoped:
        scoped.setattr(HeldArtifact, "delete", first_delete_fault)
        _fail_policy_teardown(scoped)
        _fail_held_exit(scoped, "fourth held cleanup fault")
        code, err = _invoke(case)
    records = events(audit)
    assert code == 3 and "PARTIAL:" in err
    assert "reason=first artifact delete fault" in err
    assert records[-1]["error_type"] == "SystemExit"
    assert err.index("first policy close fault") < err.index(
        "second policy notification fault") < err.index("fourth held cleanup fault")


@pytest.mark.skipif(os.name != "nt", reason="Windows exact-object deletion only")
def test_incomplete_audit_and_lifecycle_cleanup_keep_both_secondary_faults(
        tmp_path, monkeypatch):
    case = fixture(tmp_path)
    _, _, _, _, _, audit, _ = case
    _fail_before_mutation(monkeypatch, 0, OSError)
    _fail_cleanup(monkeypatch, RetentionAudit, "second audit cleanup fault")
    _fail_cleanup(monkeypatch, LifecycleLease, "third lifecycle cleanup fault")
    code, err = _invoke(case)
    records = events(audit)
    assert code == 3 and "FAILED:" in err
    assert "reason=original execution fault" in err
    assert err.index("Cleanup error: OSError: second audit cleanup fault") < err.index(
        "Cleanup error: OSError: third lifecycle cleanup fault")
    assert records[-1]["error_type"] == "OSError"
    assert f"Operation ID: {records[0]['operation_id']}" in err
    assert f"Audit: {audit}" in err


@pytest.mark.skipif(os.name != "nt", reason="Windows exact-object deletion only")
@pytest.mark.parametrize("diagnostic_fault", ["none", "write", "flush"])
def test_policy_held_failed_event_and_outer_cleanup_keep_first_fault(
        tmp_path, monkeypatch, diagnostic_fault):
    case = fixture(tmp_path)
    root, _, _, _, _, audit, _ = case
    original_append = RetentionAudit.append

    def failed_event_fault(self, event, operation_id, **fields):
        original_append(self, event, operation_id, **fields)
        if event == "failed":
            raise OSError("fourth failed-event persistence fault")

    class Diagnostic(StringIO):
        def write(self, value):
            if diagnostic_fault == "write":
                raise OSError("broken stderr write")
            return super().write(value)

        def flush(self):
            if diagnostic_fault == "flush":
                raise OSError("broken stderr flush")
            return super().flush()

    with monkeypatch.context() as scoped:
        _fail_policy_teardown(scoped)
        _fail_held_exit(scoped, "third held cleanup fault")
        _fail_cleanup(scoped, RetentionAudit, "fifth audit cleanup fault")
        _fail_cleanup(scoped, LifecycleLease, "sixth lifecycle cleanup fault")
        scoped.setattr(RetentionAudit, "append", failed_event_fault)
        code, err = _invoke(case, Diagnostic())
    records = events(audit)
    assert code == 3 and [event["event"] for event in records] == [
        "intent", "attempt", "failed"]
    assert records[-1]["error_type"] == "OSError"
    assert (root / "alpha.mp4").exists()
    if diagnostic_fault != "write":
        assert "PARTIAL:" in err and "reason=first policy close fault" in err
        assert err.index("second policy notification fault") < err.index(
            "third held cleanup fault") < err.index("fifth audit cleanup fault") < err.index(
                "sixth lifecycle cleanup fault")
        assert "Audit state may be incomplete" in err
        assert f"Operation ID: {records[0]['operation_id']}" in err
        assert f"Audit: {audit}" in err
