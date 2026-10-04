"""One known native journal owner; historical admission is never writer permission."""

import os
from pathlib import Path

import pytest

from tests.capture_handoff_helpers import authority, local_media, observations, reserve
from tikrec.capture_handoff import CaptureHandoffError
from tikrec.capture_handoff_authority import CaptureAuthority, operation_id
from tikrec.lifecycle_lock import LifecycleBusy

pytestmark = pytest.mark.skipif(os.name != "nt", reason="requires native Windows catalog ownership")


def test_second_authority_and_catalog_replacement_refused(tmp_path):
    with authority(tmp_path) as owner:
        with pytest.raises(LifecycleBusy):
            CaptureAuthority(owner.journal, owner.root)
        with pytest.raises(OSError):
            owner.journal.path.rename(owner.journal.path.with_name("other.sqlite3"))
        owner.assert_held()


def test_lost_admit_ack_then_stop_never_opens_writer_even_with_receipt_replay(tmp_path):
    data = local_media(tmp_path / "fixture.flv")
    with authority(tmp_path) as owner:
        bridge = reserve(owner)
        def fault(kind, boundary):
            if kind == "admit" and boundary == "after_commit":
                owner.journal.capture_intent(operation_id(), bridge.intent.session_id,
                                             bridge.binding["generation"], 2, stop=True, recovery="user_stop")
                raise OSError("lost admission acknowledgement")
        owner.journal._fault = fault
        with pytest.raises(CaptureHandoffError):
            bridge.run(**observations(data))
        assert not Path(bridge.intent.parts_path).exists()
        row = owner.journal.session(bridge.intent.session_id)
        assert row["stop"] == 1 and row["phase"] == "closing" and row["seal"] is None
        replay = owner.journal.admit(bridge.admit_operation, bridge.intent.session_id,
                                    bridge.binding["generation"], 1, "123")
        assert replay["revision"] == 2
        assert row == owner.journal.session(bridge.intent.session_id)


def test_lost_h_ack_is_reconciled_before_next_room_is_admitted(tmp_path):
    data = local_media(tmp_path / "fixture.flv")
    with authority(tmp_path) as owner:
        bridge = reserve(owner)
        def fault(kind, boundary):
            if kind == "handoff" and boundary == "after_commit":
                assert bridge.intent.session_id in owner.pending
                raise OSError("acknowledgement lost")
        owner.journal._fault = fault
        result = bridge.run(**observations(data))
        assert result.phase == "queued" and not owner.pending
        receipt = owner.journal.operation(bridge.handoff_operation)
        assert receipt and owner.inspect(bridge.intent.session_id)["phase"] == "queued"
        reserve(owner, "two", "456")


def test_never_admitted_resolution_failure_has_a_durable_no_writer_disposition(tmp_path):
    from tikrec.tiktok import TikTokOfflineError
    with authority(tmp_path) as owner:
        bridge = reserve(owner)
        def offline(_):
            raise TikTokOfflineError("fixture offline")
        result = bridge.run(resolver=offline, offline_confirmation_checks=1, sleeper=lambda _: None)
        assert result.phase == "no_assembly" and result.failure is not None
        row = owner.journal.session(bridge.intent.session_id)
        assert row["recovery"] == "identity_unavailable" and row["seal"] is None
        assert not owner.journal.status()["units"] and not Path(bridge.intent.parts_path).exists()


def test_existing_unclaimed_artifacts_refuse_before_reservation_writes(tmp_path):
    from tikrec.session_journal_types import JournalConflict
    with authority(tmp_path) as owner:
        path = owner.root / "one.mp4"
        path.write_bytes(b"unrelated existing media")
        before = owner.journal.status()
        with pytest.raises(JournalConflict, match="already exists"):
            reserve(owner)
        assert path.read_bytes() == b"unrelated existing media"
        assert owner.journal.status() == before and not owner.journal.history()


def test_stop_after_pending_marker_does_not_refresh_H_control_revision(tmp_path):
    data = local_media(tmp_path / "fixture.flv")
    with authority(tmp_path) as owner:
        bridge = reserve(owner)
        def fault(boundary):
            if boundary == "after_marker":
                bridge.stop()
        bridge._fault = fault
        with pytest.raises(CaptureHandoffError) as caught:
            bridge.run(**observations(data))
        assert "control revision" in str(caught.value.original)
        row = owner.journal.session(bridge.intent.session_id)
        assert row["phase"] == "closing" and row["stop"] == 1
        assert row["seal"] is None and row["task"] is None
        assert owner.journal.operation(bridge.handoff_operation) is None
        assert owner.inspect(bridge.intent.session_id)["phase"] == "closing"
