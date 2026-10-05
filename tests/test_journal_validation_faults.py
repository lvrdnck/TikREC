"""Real candidate failures, retained owners and exact receipt acknowledgement loss."""

import os
import ctypes
from ctypes import wintypes
import sqlite3
from pathlib import Path

import pytest

from tests.test_journal_validation import validated, managed_process
from tikrec.journal_validation import ValidationError

pytestmark = pytest.mark.skipif(os.name != "nt", reason="Windows validation faults")


@pytest.mark.parametrize("boundary", ["before_validation_authority", "after_validation_authority",
    "after_identity", "before_resume_fence", "native_after_resume",
    "after_validation_result", "before_validation_receipt", "after_validation_receipt"])
@pytest.mark.parametrize("change", ["inventory", "bytes"])
def test_changes_at_validation_boundaries_never_inherit_success(validated, boundary, change):
    adapter, _, _, _ = validated
    runner = adapter.coordinator
    def fault(point):
        validating = runner.children and runner.children[-1]["intent"].get("access") == "candidate_validation"
        if point == boundary and (validating or boundary in {"before_validation_authority", "after_validation_authority"}):
            if change == "inventory":
                (runner.scratch.path / "unexplained.bin").write_bytes(b"foreign")
            else:
                held = runner.scratch.artifacts["candidate.mp4"]
                os.lseek(held.fd, 0, os.SEEK_SET)
                os.write(held.fd, b"changed!")
                os.fsync(held.fd)
    runner._fault = fault
    with pytest.raises(ValidationError):
        adapter.run()
    assert not adapter.close() and not runner.guard.closed
    assert runner.scratch.artifacts["candidate.mp4"].handle is not None
    receipt = runner.journal.validation(runner.token)
    if boundary != "after_validation_receipt" and receipt is not None:
        assert receipt["evidence"] is None
    assert runner.journal.scratch(runner.token)["candidate"]["publication"] == "unpublished"


def test_native_protection_refuses_new_writer_and_replacement(validated):
    adapter, _, _, _ = validated
    runner, refused = adapter.coordinator, []
    def fault(point):
        if point == "after_validation_authority":
            path = runner.scratch.path / "candidate.mp4"
            for operation in (lambda: path.write_bytes(b"bad"), lambda: path.rename(path.with_suffix(".old"))):
                with pytest.raises(OSError):
                    operation()
                refused.append(True)
    runner._fault = fault
    assert adapter.run()["passed"] and len(refused) == 2


def test_hash_revalidation_refuses_changed_bytes_even_with_restored_stamp(validated):
    adapter, _, _, _ = validated
    runner = adapter.coordinator
    def fault(point):
        if point == "after_validation_result":
            held = runner.scratch.artifacts["candidate.mp4"]
            before = held.stamp
            os.lseek(held.fd, 0, os.SEEK_SET)
            os.write(held.fd, b"changed!")
            os.fsync(held.fd)
            written = int(before.split(":")[-1], 16)
            stamp = wintypes.FILETIME(written & 0xffffffff, written >> 32)
            held.api.SetFileTime.argtypes = (wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
                                             ctypes.POINTER(wintypes.FILETIME))
            held.api.SetFileTime.restype = wintypes.BOOL
            assert held.api.SetFileTime(held.handle, None, None, ctypes.byref(stamp))
            assert held.stamp == before
    runner._fault = fault
    with pytest.raises(ValidationError) as caught:
        adapter.run()
    assert "candidate bytes changed" in str(caught.value.original)
    assert runner.journal.validation(runner.token)["evidence"] is None


def test_post_commit_revalidation_refuses_namespace_change_in_commit_window(validated):
    adapter, _, _, _ = validated
    runner = adapter.coordinator
    def fault(kind, point):
        if kind == "finish_validation" and point == "before_commit":
            (runner.scratch.path / "late.bin").write_bytes(b"cooperative namespace drift")
    runner.journal._fault = fault
    with pytest.raises(ValidationError) as caught:
        adapter.run()
    assert "inventory changed" in str(caught.value.original)
    historical = runner.journal.validation(runner.token)
    assert historical["evidence"]["report"]["passed"]
    assert historical["binding"]["candidate"] == runner.journal.scratch(runner.token)["candidate"]
    assert not adapter.close() and not runner.guard.closed


@pytest.mark.parametrize("corruption", ["container", "decode"])
def test_actual_corrupted_candidate_keeps_failed_receipt_and_original_inputs(validated, corruption):
    adapter, _, _, _ = validated
    runner = adapter.coordinator
    def fault(point):
        if point == "after_assembly_diagnostics":
            path = runner.scratch.path / "candidate.mp4"
            data = bytearray(path.read_bytes())
            if corruption == "container":
                data[:] = b"invalid mp4 candidate"
            else:
                start = data.index(b"mdat") + 4
                size = int.from_bytes(data[start - 8:start - 4], "big") - 8
                data[start:start + size] = b"\xff" * size
            path.write_bytes(data)
    runner._fault = fault
    with pytest.raises(ValidationError) as caught:
        adapter.run()
    assert str(caught.value.original) == "candidate failed media validation"
    receipt = runner.journal.validation(runner.token)
    assert not receipt["evidence"]["report"]["passed"]
    assert receipt["evidence"]["report"]["final_output_decode"] == "failed"
    assert len(receipt["evidence"]["children"]) == 3
    assert not adapter.close() and not runner.guard.closed


@pytest.mark.parametrize("unavailable", [False, True])
@pytest.mark.parametrize("operation_kind", ["begin_validation", "finish_validation"])
def test_validation_receipt_ack_loss_reconciles_only_once(validated, monkeypatch, unavailable, operation_kind):
    adapter, _, _, _ = validated
    runner = adapter.coordinator
    lookups, operation = [], runner.journal.operation
    def lookup(identity):
        lookups.append(identity)
        if unavailable:
            raise OSError("receipt unavailable")
        return operation(identity)
    def fault(kind, point):
        if kind == operation_kind and point == "after_commit":
            raise OSError("validation acknowledgement lost")
    runner.journal._fault = fault
    monkeypatch.setattr(runner.journal, "operation", lookup)
    if unavailable:
        with pytest.raises(ValidationError):
            adapter.run()
    else:
        assert adapter.run()["passed"]
    assert len(lookups) == 1
    receipt = runner.journal.validation(runner.token)
    if operation_kind == "begin_validation" and unavailable:
        assert receipt["evidence"] is None
    else:
        assert receipt["evidence"]["report"]["passed"]
    assert not adapter.close() and not runner.guard.closed


@pytest.mark.parametrize("failure", ["observer", "eof", "native_cleanup", "first_and_secondary"])
def test_validation_failure_retains_native_protection_and_first_error(validated, monkeypatch, failure):
    import tikrec.journal_validation as module
    adapter, _, _, _ = validated
    runner = adapter.coordinator
    first = OSError("first validation failure")
    def unavailable(*_):
        raise first
    def fault(point):
        if point == "native_after_resume" and runner.children[-1]["intent"].get("access") == "candidate_validation":
            native = runner.children[-1]["process"].native
            if failure in {"native_cleanup", "first_and_secondary"}:
                monkeypatch.setattr(native, "close", lambda: (_ for _ in ()).throw(OSError("secondary cleanup")))
            if failure == "eof":
                status = native.status
                def exited():
                    value = status()
                    if value[0] is not None and value[1] == 0:
                        native.streams.eof.clear()
                        monkeypatch.setattr(native.streams, "read", unavailable)
                    return value
                monkeypatch.setattr(native, "status", exited)
    runner._fault = fault
    if failure in {"observer", "first_and_secondary"}:
        monkeypatch.setattr(module.ValidationDiagnostics, "observe", unavailable)
    with pytest.raises(ValidationError) as caught:
        adapter.run()
    if failure in {"observer", "first_and_secondary"}:
        assert caught.value.original is first
    assert runner.journal.validation(runner.token)["evidence"] is None
    assert not adapter.close() and not runner.guard.closed
    assert runner.scratch.artifacts["candidate.mp4"].handle is not None


def test_validation_and_receipt_rows_are_immutable(validated):
    adapter, _, _, _ = validated
    adapter.run()
    with sqlite3.connect(adapter.coordinator.journal.path) as db:
        for table in ("candidate_validations", "validation_receipts"):
            with pytest.raises(sqlite3.IntegrityError):
                db.execute(f"DELETE FROM {table}")
            with pytest.raises(sqlite3.IntegrityError):
                db.execute(f"UPDATE {table} SET token=token")
