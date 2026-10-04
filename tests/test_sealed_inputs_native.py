"""Real Windows sharing, namespace ambiguity and retained cleanup ownership."""

import ctypes
import os
from pathlib import Path

import pytest

from tests.sealed_input_helpers import acquire, hashes, sealed
from tikrec.capture_handoff_native import NativeHandle

pytestmark = pytest.mark.skipif(os.name != "nt", reason="native Windows read protection")


def test_capture_shared_mode_is_not_immutable_protection(tmp_path):
    path = tmp_path / "identity-only"
    path.write_bytes(b"initial")
    with NativeHandle(path, shared=True):
        with path.open("ab") as writer:
            writer.write(b"allowed")
    assert path.read_bytes() == b"initialallowed"


def test_readers_allowed_data_writes_delete_and_rename_denied(sealed):
    owner, bridge, _ = sealed
    parts = Path(bridge.intent.parts_path)
    paths = list(parts.iterdir())
    with acquire(sealed) as guard:
        for path in paths:
            with path.open("rb") as reader:
                assert reader.read(1)
            with pytest.raises(OSError):
                path.open("ab")
            with pytest.raises(OSError):
                path.unlink()
            with pytest.raises(OSError):
                path.rename(path.with_name("renamed"))
        with pytest.raises(OSError):
            parts.rename(parts.with_name("renamed.parts"))
        for held in guard.handles:
            flags = ctypes.c_ulong()
            api = held.api
            api.GetHandleInformation.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
            assert api.GetHandleInformation(held.handle, ctypes.byref(flags))
            assert not flags.value & 1
        guard.revalidate()
    with paths[0].open("ab"):
        pass


@pytest.mark.parametrize("conflict", ["media_writer", "control_writer", "marker_writer", "exclusive_reader"])
def test_existing_conflicting_handle_refuses_without_mutation(sealed, conflict):
    owner, bridge, _ = sealed
    parts = Path(bridge.intent.parts_path)
    path = parts / {"media_writer": "part-0001.flv", "control_writer": "session.json",
                    "marker_writer": "finalization-owner.json", "exclusive_reader": "part-0001.flv"}[conflict]
    existing = NativeHandle(path) if conflict == "exclusive_reader" else path.open("ab")
    before, status = hashes(owner.root.parent) if conflict != "exclusive_reader" else None, owner.journal.status()
    try:
        with pytest.raises(Exception) as failure:
            acquire(sealed)
        assert not failure.value.guard.retained
        assert owner.journal.status() == status
        if before is not None:
            assert hashes(owner.root.parent) == before
    finally:
        existing.close()


@pytest.mark.parametrize("kind", ["hardlink", "symlink", "directory_redirect"])
def test_redirected_or_multiply_linked_evidence_refused(sealed, kind):
    owner, bridge, _ = sealed
    parts = Path(bridge.intent.parts_path)
    source = parts / "part-0001.flv"
    if kind == "hardlink":
        os.link(source, owner.root / "alias.flv")
    else:
        try:
            if kind == "symlink":
                source.unlink()
                source.symlink_to(owner.root.parent / "source.flv")
            else:
                alternate = owner.root / "moved.parts"
                parts.rename(alternate)
                parts.symlink_to(alternate, target_is_directory=True)
        except OSError as error:
            pytest.skip("Windows symlink privilege unavailable: " + str(error))
    before = owner.journal.status()
    with pytest.raises(Exception) as failure:
        acquire(sealed)
    assert owner.journal.status() == before and not failure.value.guard.retained


def test_case_alias_resolves_exact_native_identity(sealed):
    _, bridge, _ = sealed
    parts = Path(bridge.intent.parts_path)
    source = parts / "part-0001.flv"
    source.rename(parts / "PART-0001.FLV")
    with acquire(sealed) as guard:
        assert guard.revalidate().flv_inputs[0].read_bytes()
