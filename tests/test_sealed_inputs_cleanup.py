"""Exact native and lifecycle ownership across acquisition and teardown faults."""

import ctypes
import os
from pathlib import Path

import pytest

from tests.sealed_input_helpers import acquire, hashes, sealed
from tikrec.capture_handoff_native import NativeHandle

pytestmark = pytest.mark.skipif(os.name != "nt", reason="native Windows read protection")


@pytest.mark.parametrize("boundary", ["after_lifecycle", "before_inventory", "after_open_2", "after_inventory"])
def test_partial_acquisition_failure_keeps_original_and_releases_all(sealed, boundary):
    owner, _, _ = sealed
    original = OSError("acquisition fault")
    before = hashes(owner.root.parent)
    def fault(point):
        if point == boundary:
            raise original
    with pytest.raises(Exception) as failure:
        acquire(sealed, fault=fault)
    assert failure.value.original is original
    assert failure.value.guard.closed and not failure.value.guard.retained
    assert hashes(owner.root.parent) == before


def test_native_cleanup_failure_retains_exact_handle_and_original(sealed, monkeypatch):
    from tikrec.sealed_input_native import ReadProtection
    real_close = ReadProtection.close
    original, cleanup = OSError("inventory failure"), OSError("close refused")
    retained = []
    def close(held):
        if held.path.name == "part-0001.flv" and not retained:
            retained.append(held)
            raise cleanup
        return real_close(held)
    monkeypatch.setattr(ReadProtection, "close", close)
    def fault(point):
        if point == "after_inventory":
            raise original
    with pytest.raises(Exception) as failure:
        acquire(sealed, fault=fault)
    error = failure.value
    assert error.original is original and cleanup in error.diagnostics
    assert retained[0] in error.guard.retained and retained[0].handle is not None
    with pytest.raises(OSError):
        retained[0].path.open("ab")
    error.guard.close()
    assert error.guard.closed and not error.guard.retained


def test_missing_or_short_lifecycle_file_is_not_initialized(sealed):
    owner, _, _ = sealed
    lock = owner.root / ".tikrec-lifecycle.lock"
    for missing in (True, False):
        lock.unlink(missing_ok=True)
        if not missing:
            lock.write_bytes(b"short")
        with pytest.raises(Exception):
            acquire(sealed)
        assert not lock.exists() if missing else lock.read_bytes() == b"short"


def test_new_children_are_detected_during_guard_lifetime(sealed):
    _, bridge, _ = sealed
    parts = Path(bridge.intent.parts_path)
    with acquire(sealed) as guard:
        # A directory pin does not deny child creation: complete inventory checks
        # enforce the cooperative namespace contract, not a fictional OS guarantee.
        extra = parts / "part-0002.flv"
        extra.write_bytes(b"unexplained")
        with pytest.raises(Exception, match="inventory"):
            guard.revalidate()
        assert extra.read_bytes() == b"unexplained"


def test_native_open_validation_fault_retains_owner_before_cleanup(sealed, monkeypatch):
    from tikrec.sealed_input_native import ReadProtection
    real_info, real_close = ReadProtection._information, ReadProtection.close
    original, cleanup = OSError("native information failed"), OSError("native close failed")
    kept = []
    def information(held):
        if held.path.name == "part-0001.flv":
            raise original
        return real_info(held)
    def close(held):
        if held.path.name == "part-0001.flv" and not kept:
            kept.append(held)
            raise cleanup
        real_close(held)
    monkeypatch.setattr(ReadProtection, "_information", information)
    monkeypatch.setattr(ReadProtection, "close", close)
    with pytest.raises(Exception) as failure:
        acquire(sealed)
    assert failure.value.original is original and cleanup in failure.value.diagnostics
    assert kept[0].handle is not None and kept[0] in failure.value.guard.retained
    failure.value.guard.close()
    assert not failure.value.guard.retained


def test_lifecycle_acquisition_failure_keeps_failed_close_owner(sealed, monkeypatch):
    import tikrec.lifecycle_lock as lifecycle
    real_open = lifecycle._open_lock
    original, cleanup = OSError("lease acquisition failed"), OSError("lease file close failed")
    class File:
        def __init__(self, actual):
            self.actual, self.failed = actual, False
        @property
        def closed(self):
            return self.actual.closed
        def close(self):
            if not self.failed:
                self.failed = True
                raise cleanup
            self.actual.close()
    monkeypatch.setattr(lifecycle, "_open_lock", lambda *a: File(real_open(*a)))
    def fail(*_):
        raise original
    monkeypatch.setattr(lifecycle, "_lock", fail)
    with pytest.raises(Exception) as failure:
        acquire(sealed)
    assert failure.value.original is original and cleanup in failure.value.diagnostics
    # The guard retries the retained exact owner, so this one-shot close failure
    # is reported even though native release is eventually confirmed.
    assert failure.value.guard.closed and not failure.value.guard.retained


def test_lifecycle_teardown_failure_remains_reachable_and_retryable(sealed):
    guard = acquire(sealed)
    actual = guard.lifecycle.handle
    cleanup = OSError("lease close refused")
    class File:
        @property
        def closed(self):
            return actual.closed
        def seek(self, *args):
            return actual.seek(*args)
        def fileno(self):
            return actual.fileno()
        def close(self):
            raise cleanup
    guard.lifecycle.handle = File()
    with pytest.raises(Exception) as failure:
        guard.close()
    assert failure.value.original is cleanup and not guard.closed
    assert guard.lifecycle in guard.retained
    guard.lifecycle.handle = actual
    guard.close()
    assert guard.closed and not guard.retained and cleanup in guard.cleanup_errors


def test_body_failure_preserved_with_cleanup_evidence(sealed, monkeypatch):
    from tikrec.sealed_input_native import ReadProtection
    guard = acquire(sealed)
    original, cleanup = RuntimeError("reader failed"), OSError("teardown failed")
    real_close, kept = ReadProtection.close, []
    def close(held):
        if held.path.name == "part-0001.flv" and not kept:
            kept.append(held)
            raise cleanup
        real_close(held)
    monkeypatch.setattr(ReadProtection, "close", close)
    with pytest.raises(RuntimeError) as failure:
        with guard:
            raise original
    assert failure.value is original and original.sealed_input_guard is guard
    assert cleanup in original.sealed_input_cleanup and not guard.closed
    guard.close()


def test_directory_junction_is_refused_without_symlink_privilege(sealed):
    import subprocess
    owner, bridge, _ = sealed
    parts = Path(bridge.intent.parts_path)
    moved = parts.with_name("junction-target.parts")
    parts.rename(moved)
    subprocess.run([os.environ["COMSPEC"], "/d", "/c", "mklink", "/J", str(parts), str(moved)],
                   check=True, capture_output=True, timeout=5)
    before = owner.journal.status()
    with pytest.raises(Exception) as failure:
        acquire(sealed)
    assert not failure.value.guard.retained and owner.journal.status() == before
    assert (moved / "part-0001.flv").read_bytes()


def test_concurrent_revalidation_and_repeated_close_is_serialized(sealed):
    from concurrent.futures import ThreadPoolExecutor
    guard = acquire(sealed)
    with ThreadPoolExecutor(max_workers=8) as pool:
        validations = [pool.submit(guard.revalidate) for _ in range(8)]
        assert all(f.result(timeout=10).seal_hash == guard.seal_hash for f in validations)
        closes = [pool.submit(guard.close) for _ in range(8)]
        assert all(f.result(timeout=10) is None for f in closes)
    assert guard.closed and not guard.retained


def test_closehandle_failure_does_not_clear_exact_native_owner(sealed, monkeypatch):
    guard = acquire(sealed)
    held = guard.files[0]
    exact = held.handle
    real_close = held.api.CloseHandle
    def fail(_):
        ctypes.set_last_error(5)
        return 0
    monkeypatch.setattr(held.api, "CloseHandle", fail)
    with pytest.raises(Exception):
        guard.close()
    assert held.handle == exact and held in guard.retained and not guard.closed
    with pytest.raises(OSError):
        held.path.open("ab")
    monkeypatch.setattr(held.api, "CloseHandle", real_close)
    guard.close()
    assert held.handle is None and guard.closed and not guard.retained
