"""Confirmed journal transfer survives later native teardown and projection faults."""

import os
from pathlib import Path

import pytest

from tests.capture_handoff_helpers import authority, contents, local_media, observations, reserve
from tikrec.capture_handoff_authority import CaptureAuthority
from tikrec.capture_handoff_native import NativeHandle
from tikrec.lifecycle_lock import acquire_lifecycle
from tikrec.session_journal import SessionJournal
from tikrec.session_journal_types import JournalError

pytestmark = pytest.mark.skipif(os.name != "nt", reason="requires native Windows post-H teardown")


@pytest.mark.parametrize("empty", [False, True])
@pytest.mark.parametrize("artifact", ["session.json", "finalization-owner.json"])
@pytest.mark.parametrize("lost_ack", [False, True])
def test_confirmed_transfer_survives_native_teardown_and_releases_capture_lease(
        tmp_path, monkeypatch, empty, artifact, lost_ack):
    data = local_media(tmp_path / "fixture.flv")
    with authority(tmp_path) as owner:
        bridge = reserve(owner, raw=False)
        error = OSError("post-H native teardown failed")
        original_close = NativeHandle.close
        observed = []
        def close(held):
            was_open = held.handle is not None
            original_close(held)
            if was_open and held.path == Path(bridge.intent.parts_path, artifact):
                row = owner.journal.session(bridge.intent.session_id)
                assert row["phase"] == ("no_assembly" if empty else "queued")
                assert not owner.pending
                observed.append(error)
                raise error
        monkeypatch.setattr(NativeHandle, "close", close)
        if lost_ack:
            def fault(kind, boundary):
                if kind == ("settle_empty_capture" if empty else "handoff") and boundary == "after_commit":
                    raise OSError("lost H acknowledgement")
            owner.journal._fault = fault
        options = observations(data)
        if empty:
            options["tag_source"] = lambda _: iter(())
        projected = []
        result = bridge.run(notify=projected.append, **options)
        # The injected close fault targets capture teardown, not later inspection handles.
        monkeypatch.setattr(NativeHandle, "close", original_close)
        assert observed == [error] and result.post_h_errors == (error,)
        assert result.phase == ("no_assembly" if empty else "queued")
        assert result.failure is None and result.notification_error is None
        assert projected == [result.receipt] and bridge.failure is None
        assert bridge.lease.closed and bridge.lease.handle.closed and not bridge.fence.active
        # Acquisition alone proves no leaked capture lifecycle owner; no retention runs.
        with acquire_lifecycle(owner.root, "retention"):
            pass
        row = owner.journal.session(bridge.intent.session_id)
        before = contents(Path(bridge.intent.parts_path))
        status = owner.journal.status()
        assert all(b["session"] is None for b in status["bindings"])
        assert status["units"] == [{"session": bridge.intent.session_id,
                                    "kind": "evidence" if empty else "task"}]
        assert len(status["tasks"]) == (0 if empty else 1)
        assert row["seal"]["disposition"] == ("empty" if empty else "assembly")
        assert not Path(result.requested_output).exists()
        assert owner.inspect(bridge.intent.session_id)["source_resume_allowed"] is False
        with pytest.raises(JournalError, match="single-use"):
            bridge.run(**observations(data))
        method = owner.journal.settle_empty_capture if empty else owner.journal.handoff
        from tikrec.session_journal_types import closure_from_record, encode
        replay = method(bridge.handoff_operation, bridge.intent.session_id, bridge.binding["generation"],
                        result.receipt["revision"] - 1, closure_from_record(encode(row["seal"])))
        assert replay == result.receipt and owner.journal.status() == status
        next_bridge = reserve(owner, "two", "456", raw=False, slot=1)
        assert next_bridge.binding["generation"] == bridge.binding["generation"] + 1
        assert owner.journal.session(bridge.intent.session_id) == row
        assert contents(Path(bridge.intent.parts_path)) == before
        path, catalog, root = owner.journal.path, owner.journal.catalog_id, owner.root
    with CaptureAuthority(SessionJournal(path, catalog), root) as reopened:
        assert reopened.journal.session(bridge.intent.session_id) == row
        inspected = reopened.inspect(bridge.intent.session_id)
        assert inspected["phase"] == result.phase and inspected["source_resume_allowed"] is False
        assert len([u for u in reopened.journal.status()["units"]
                    if u["session"] == bridge.intent.session_id]) == 1


@pytest.mark.parametrize("empty", [False, True])
def test_post_H_fault_does_not_skip_lease_release_or_lose_projection_diagnostics(tmp_path, monkeypatch, empty):
    data = local_media(tmp_path / "fixture.flv")
    with authority(tmp_path) as owner:
        bridge = reserve(owner, raw=False)
        confirmed_error, marker_error, input_error, lease_error, projection_error = [OSError(name) for name in
            ("after confirmed H", "marker teardown", "input teardown", "after lease release", "projection failed")]
        def fault(boundary):
            if boundary == "confirmed_h":
                raise confirmed_error
        bridge._fault = fault
        native_close = NativeHandle.close
        def close_native(held):
            was_open = held.handle is not None
            native_close(held)
            if was_open and held.path.parent == Path(bridge.intent.parts_path):
                if held.path.name == "finalization-owner.json":
                    raise marker_error
                if held.path.name == "session.json":
                    raise input_error
        monkeypatch.setattr(NativeHandle, "close", close_native)
        original_close = bridge.lease.close
        def close():
            was_open = not bridge.lease.closed
            original_close()
            if was_open:
                raise lease_error
        monkeypatch.setattr(bridge.lease, "close", close)
        def notify(_):
            assert bridge.lease.closed and bridge.lease.handle.closed
            raise projection_error
        options = observations(data)
        if empty:
            options["tag_source"] = lambda _: iter(())
        result = bridge.run(notify=notify, **options)
        assert result.post_h_errors == (confirmed_error, marker_error, input_error, lease_error, projection_error)
        assert result.notification_error is projection_error and result.failure is None
        assert bridge.lease.closed and not owner.pending
        with acquire_lifecycle(owner.root, "retention"):
            pass
        monkeypatch.setattr(NativeHandle, "close", native_close)
        assert owner.inspect(bridge.intent.session_id)["phase"] == result.phase
        assert owner.inspect(bridge.intent.session_id)["source_resume_allowed"] is False
