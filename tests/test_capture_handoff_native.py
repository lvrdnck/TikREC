"""Native handle exclusivity, alias identity and evidence refusal on Windows."""

import os

import pytest

from tikrec.capture_handoff_native import NativeHandle, child_identity
from tikrec.session_journal_types import JournalError

pytestmark = pytest.mark.skipif(os.name != "nt", reason="requires Windows native handles")


def test_native_file_and_volume_identity_is_held_and_writer_exclusive(tmp_path):
    path = tmp_path / "input.flv"
    path.write_bytes(b"fixture")
    with path.open("ab"):
        with pytest.raises(OSError):
            NativeHandle(path)
    with NativeHandle(path) as held:
        assert held.identity.volume.startswith("volume{") and held.size == 7
        assert held.identity.components[-1] == "input.flv"
        held.flush()
        assert held.read_control() == b"fixture"
        held.verify()
        with pytest.raises(OSError):
            path.open("ab")
        with pytest.raises(OSError):
            path.rename(tmp_path / "replacement.flv")
    path.rename(tmp_path / "released.flv")


def test_absent_child_case_alias_and_multiply_linked_file_refusal(tmp_path):
    with NativeHandle(tmp_path, directory=True) as parent:
        assert child_identity(parent, "Alias.mp4") == child_identity(parent, "alias.MP4")
    first, second = tmp_path / "one.flv", tmp_path / "two.flv"
    first.write_bytes(b"same object")
    os.link(first, second)
    with pytest.raises(JournalError, match="multiply-linked"):
        NativeHandle(first)


def test_native_teardown_preserves_original_failure_and_cleanup_evidence(tmp_path, monkeypatch):
    path = tmp_path / "input.flv"
    path.write_bytes(b"fixture")
    held = NativeHandle(path)
    original_close = held.close
    def fail():
        original_close()
        raise OSError("secondary native close failure")
    monkeypatch.setattr(held, "close", fail)
    original = ValueError("mandatory original flush failure")
    with pytest.raises(ValueError) as caught:
        with held:
            raise original
    assert caught.value is original and original.capture_cleanup_errors


def test_existing_child_identity_is_resolved_from_its_native_handle(tmp_path):
    path = tmp_path / "LongCaptureName.parts"
    path.mkdir()
    with NativeHandle(tmp_path, directory=True) as parent, NativeHandle(path, directory=True) as child:
        assert child_identity(parent, path.name.upper()) == child.identity
