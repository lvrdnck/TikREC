"""Public retention results at held-artifact and mutation cleanup boundaries."""

import os
from contextlib import contextmanager
from io import StringIO

import pytest

from tests.test_retention_execute import events, fixture
from tests.test_retention_plan import NOW, inspect
from tests.test_retention_primary_result import _fail_cleanup, _invoke
from tikrec.retention_audit import RetentionAudit
from tikrec.retention_windows import HeldArtifact


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
