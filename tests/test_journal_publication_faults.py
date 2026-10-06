"""Fresh native evidence, immutable receipts and uncertainty without replay."""

import ctypes
import os
import sqlite3
from ctypes import wintypes
from pathlib import Path

import pytest

from tests.journal_publication_helpers import publishing
from tests.journal_assembly_helpers import managed_process
from tikrec.candidate_publication import CandidatePublication
from tikrec.journal_publication import PublicationError

pytestmark = pytest.mark.skipif(os.name != "nt", reason="native Windows publication faults")

BOUNDARIES = ["before_publication_preparation", "after_publication_preparation", "before_publication_fence",
              "after_publication_native", "before_publication_result", "after_publication_result"]


@pytest.mark.parametrize("boundary", BOUNDARIES)
@pytest.mark.parametrize("mutation", ["inventory", "bytes"])
def test_all_publication_boundaries_revalidate_inventory_and_restored_stamp_bytes(publishing, boundary, mutation):
    adapter, bridge, _, _ = publishing
    runner = adapter.coordinator
    def fault(point):
        if point != boundary:
            return
        if mutation == "inventory":
            (runner.scratch.path / "foreign.bin").write_bytes(b"unexpected inventory")
        else:
            held = runner.scratch.artifacts["candidate.mp4"]
            stamp = held.stamp
            os.lseek(held.fd, 0, os.SEEK_SET)
            os.write(held.fd, b"mutated!")
            os.fsync(held.fd)
            written = int(stamp.split(":")[-1], 16)
            restored = wintypes.FILETIME(written & 0xffffffff, written >> 32)
            held.api.SetFileTime.argtypes = (wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
                                             ctypes.POINTER(wintypes.FILETIME))
            held.api.SetFileTime.restype = wintypes.BOOL
            assert held.api.SetFileTime(held.handle, None, None, ctypes.byref(restored))
            assert held.stamp == stamp
    runner._fault = fault
    with pytest.raises(PublicationError) as caught:
        adapter.run()
    assert "changed" in str(caught.value.original)
    assert Path(bridge.intent.output_path).exists() == (boundary in BOUNDARIES[3:])
    record = runner.journal.publication(runner.token)
    if boundary == "after_publication_result":
        assert record["evidence"]["state"] == "observed_published"
    elif record:
        assert record["evidence"] is None
    assert not adapter.close() and runner.scratch.artifacts["candidate.mp4"].handle is not None


@pytest.mark.parametrize("kind", ["prepare_publication", "observe_publication"])
@pytest.mark.parametrize("unavailable", [False, True])
def test_ack_loss_reconciles_one_exact_operation_and_never_replays(publishing, monkeypatch, kind, unavailable):
    adapter, bridge, _, _ = publishing
    runner = adapter.coordinator
    calls, native_calls = [], []
    lookup = runner.journal.operation
    from tikrec import candidate_publication as module
    native = module.rename_no_replace
    def rename(*args):
        native_calls.append(1)
        return native(*args)
    def operation(identity):
        calls.append(identity)
        if unavailable:
            raise OSError("exact acknowledgement unavailable")
        return lookup(identity)
    def fault(selected, point):
        if selected == kind and point == "after_commit":
            raise OSError("lost acknowledgement")
    monkeypatch.setattr(module, "rename_no_replace", rename)
    monkeypatch.setattr(runner.journal, "operation", operation)
    runner.journal._fault = fault
    if unavailable:
        with pytest.raises(PublicationError):
            adapter.run()
    else:
        assert adapter.run()["state"] == "observed_published"
    assert len(calls) == 1
    assert len(native_calls) == (0 if unavailable and kind == "prepare_publication" else 1)
    assert Path(bridge.intent.output_path).exists() == bool(native_calls)
    with pytest.raises(Exception):
        adapter.run()
    assert len(native_calls) <= 1


def test_native_last_moment_collision_has_no_overwrite(publishing, monkeypatch):
    adapter, bridge, _, _ = publishing
    from tikrec import candidate_publication as module
    native = module.rename_no_replace
    def rename(*args):
        Path(bridge.intent.output_path).write_bytes(b"last-moment collision")
        return native(*args)
    monkeypatch.setattr(module, "rename_no_replace", rename)
    with pytest.raises(PublicationError) as caught:
        adapter.run()
    assert isinstance(caught.value.original, OSError)
    assert Path(bridge.intent.output_path).read_bytes() == b"last-moment collision"
    assert (adapter.coordinator.scratch.path / "candidate.mp4").exists()
    assert adapter.coordinator.journal.publication(adapter.coordinator.token)["evidence"] is None


@pytest.mark.parametrize("after_native", [False, True])
def test_uncertain_native_operation_never_replays_or_discards_original_owner(publishing, monkeypatch, after_native):
    adapter, bridge, _, _ = publishing
    from tikrec import candidate_publication as module
    native, calls = module.rename_no_replace, []
    first = OSError("uncertain native result")
    def rename(*args):
        calls.append(1)
        if after_native:
            native(*args)
        raise first
    monkeypatch.setattr(module, "rename_no_replace", rename)
    with pytest.raises(PublicationError) as caught:
        adapter.run()
    assert caught.value.original is first and calls == [1]
    assert Path(bridge.intent.output_path).exists() == after_native
    assert adapter.coordinator.scratch.artifacts["candidate.mp4"].handle is not None
    assert adapter.coordinator.journal.publication(adapter.coordinator.token)["evidence"] is None
    with pytest.raises(Exception):
        adapter.capability.promote()
    assert calls == [1]


@pytest.mark.parametrize("drift", ["identity", "parent", "volume", "alias", "replacement"])
def test_namespace_identity_parent_and_alias_drift_refused(publishing, monkeypatch, drift):
    adapter, bridge, _, _ = publishing
    runner = adapter.coordinator
    def fault(point):
        if point != "after_publication_preparation":
            return
        held = runner.scratch.artifacts["candidate.mp4"]
        if drift in {"identity", "volume"}:
            from tikrec.session_journal_types import ArtifactIdentity
            identity = held.identity
            monkeypatch.setattr(held, "identity", ArtifactIdentity("other-volume" if drift == "volume" else identity.volume,
                identity.components + ("wrong",)))
        elif drift == "parent":
            monkeypatch.setattr(adapter.capability, "output", runner.authority.root.parent / "escape.mp4")
        elif drift == "alias":
            os.link(runner.authority.root / "unrelated.bin", bridge.intent.output_path)
        else:
            # Real delete/replace attempts are refused while the original owner is held.
            with pytest.raises(OSError):
                os.replace(runner.authority.root / "unrelated.bin", held.path)
            raise RuntimeError("replacement refused")
    runner._fault = fault
    with pytest.raises(PublicationError):
        adapter.run()
    assert runner.journal.publication(runner.token)["evidence"] is None


def test_historical_passed_validation_does_not_create_another_live_capability(publishing):
    adapter, _, _, _ = publishing
    adapter.run()
    assert adapter.coordinator.journal.validation(adapter.coordinator.token)["evidence"]["report"]["passed"]
    with pytest.raises(Exception, match="already allocated"):
        CandidatePublication(adapter.validation)


@pytest.mark.parametrize("kind", ["prepare_publication", "observe_publication"])
def test_journal_first_failure_survives_secondary_hold_failure(publishing, monkeypatch, kind):
    adapter, _, _, _ = publishing
    runner = adapter.coordinator
    first = RuntimeError("first publication journal failure")
    def fault(selected, point):
        if selected == kind and point == "before_commit":
            raise first
    runner.journal._fault = fault
    scratch = runner.journal.scratch
    def unavailable(token):
        if runner.cancelled.is_set():
            raise OSError("secondary hold unavailable")
        return scratch(token)
    monkeypatch.setattr(runner.journal, "scratch", unavailable)
    with pytest.raises(PublicationError) as caught:
        adapter.run()
    assert caught.value.original is first
    assert any("secondary hold unavailable" in str(e) for e in runner.errors)
    assert runner.scratch.artifacts["candidate.mp4"].handle is not None


def test_existing_destination_fails_before_preparation(publishing):
    adapter, bridge, _, _ = publishing
    def fault(point):
        if point == "after_validation_receipt":
            Path(bridge.intent.output_path).write_bytes(b"existing destination preserved")
    adapter.coordinator._fault = fault
    with pytest.raises(PublicationError):
        adapter.run()
    assert Path(bridge.intent.output_path).read_bytes() == b"existing destination preserved"
    assert adapter.coordinator.journal.publication(adapter.coordinator.token) is None


def test_immutable_publication_facts_and_native_namespace_pins(publishing):
    adapter, bridge, _, _ = publishing
    adapter.run()
    runner = adapter.coordinator
    with sqlite3.connect(runner.journal.path) as db:
        for table in ("publication_preparations", "publication_results"):
            with pytest.raises(sqlite3.IntegrityError):
                db.execute(f"DELETE FROM {table}")
            with pytest.raises(sqlite3.IntegrityError):
                db.execute(f"UPDATE {table} SET token=token")
    with pytest.raises(OSError):
        Path(bridge.intent.output_path).write_bytes(b"replacement data")
    with pytest.raises(OSError):
        os.rename(runner.authority.root, runner.authority.root.with_name("renamed-parent"))
    with pytest.raises(OSError):
        os.rename(bridge.intent.output_path, runner.authority.root / "renamed-output.mp4")


def test_validation_only_defaults_cannot_publish(tmp_path, managed_process):
    import shutil
    from tests.capture_handoff_helpers import authority
    from tests.journal_assembly_helpers import queue_media
    from tikrec.journal_validation import JournalValidation
    with authority(tmp_path) as owner:
        queue_media(owner, tmp_path)
        def factory(sid, token):
            process = managed_process()
            process.session_id, process.attempt_token = sid, token
            return process
        adapter = JournalValidation(owner, ffmpeg=Path(shutil.which("ffmpeg")).resolve(),
            ffprobe=Path(shutil.which("ffprobe")).resolve(), process_factory=factory)
        try:
            assert adapter.run()["passed"]
            with pytest.raises(Exception, match="publication-capable"):
                CandidatePublication(adapter)
            assert owner.journal.publication(adapter.coordinator.token) is None
        finally:
            adapter.close()
            for held in [*adapter.coordinator.scratch.artifacts.values(), adapter.coordinator.scratch.workspace]:
                held.close()
            adapter.coordinator.guard.close()


@pytest.mark.parametrize("kind", ["prepare_publication", "observe_publication"])
def test_commit_window_inventory_drift_is_not_live_success(publishing, kind):
    adapter, bridge, _, _ = publishing
    runner = adapter.coordinator
    def fault(selected, point):
        if selected == kind and point == "before_commit":
            (runner.scratch.path / "commit-window.bin").write_bytes(b"late namespace change")
    runner.journal._fault = fault
    with pytest.raises(PublicationError) as caught:
        adapter.run()
    assert "inventory changed" in str(caught.value.original)
    record = runner.journal.publication(runner.token)
    assert record is not None
    assert (record["evidence"] is not None) == (kind == "observe_publication")
    assert Path(bridge.intent.output_path).exists() == (kind == "observe_publication")
    assert not adapter.close() and runner.scratch.artifacts["candidate.mp4"].handle is not None
