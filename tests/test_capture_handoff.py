"""Capture-only close uses real writer/raw/control/journal before capacity reuse."""

import os
from pathlib import Path

import pytest

from tests.capture_handoff_helpers import authority, contents, local_media, manifest, observations, reserve
from tikrec.capture_handoff import CaptureHandoffError
from tikrec.session_journal_types import JournalConflict, JournalError

pytestmark = pytest.mark.skipif(os.name != "nt", reason="requires Windows native handoff proof")


def test_repeated_original_stop_after_marker_keeps_handoff_revision(tmp_path):
    data = local_media(tmp_path / 'fixture.flv')
    from tikrec.source import iter_tags
    with authority(tmp_path) as owner:
        bridge = reserve(owner)
        def source(_, raw):
            raw.write(data)
            for index, tag in enumerate(iter_tags((data,))):
                yield tag
                if index == 10:
                    bridge.stop()
        repeated = []
        def fault(point):
            if point == 'after_marker':
                before = owner.journal.session(bridge.intent.session_id)
                bridge.stop()
                assert owner.journal.session(bridge.intent.session_id) == before
                repeated.append(True)
        bridge._fault = fault
        assert bridge.run(**observations(data, source=source)).phase == 'queued'
        assert repeated == [True] and owner.journal.session(bridge.intent.session_id)['stop']
        assert len(owner.journal.status()['units']) == 1


def test_real_room_handoff_then_same_creator_distinct_room_preserves_identity(tmp_path):
    data = local_media(tmp_path / "fixture.flv")
    with authority(tmp_path) as owner:
        escaped = []
        old = reserve(owner)
        result = old.run(**observations(data, escaped=escaped))
        assert result.phase == "queued" and not Path(result.requested_output).exists()
        assert manifest(old)["finalization"]["status"] == "pending"
        previous = owner.journal.session(old.intent.session_id)
        before = contents(Path(old.intent.parts_path))
        assert Path(old.intent.parts_path, "connection-0001.raw").read_bytes() == data
        assert owner.inspect(old.intent.session_id)["phase"] == "queued"
        new = reserve(owner, "two", "456", raw=False, slot=1)
        assert new.binding["generation"] == old.binding["generation"] + 1
        new.run(**observations(data, "456"))
        status = owner.journal.status()
        assert [t["session"] for t in status["tasks"]] == [old.intent.session_id, new.intent.session_id]
        assert all(b["session"] is None for b in status["bindings"])
        assert owner.journal.session(old.intent.session_id) == previous
        assert owner.journal.automatic_receipt(old.intent.automatic_claim)["session"] == old.intent.session_id
        assert contents(Path(old.intent.parts_path)) == before
        assert owner.journal.session(new.intent.session_id)["intent"]["raw_copy"] is False
        with pytest.raises(JournalConflict):
            escaped[0].write(b"late raw bytes")
        with pytest.raises(JournalError, match="single-use"):
            old.run(**observations(data))


def test_two_handed_off_sessions_leave_two_new_native_capture_bindings(tmp_path):
    data = local_media(tmp_path / "fixture.flv")
    with authority(tmp_path) as owner:
        first, second = reserve(owner), reserve(owner, "two", "222", "other", raw=False)
        first.run(**observations(data))
        second.run(**observations(data, "222"))
        original = [owner.journal.session(b.intent.session_id) for b in (first, second)]
        new_one = reserve(owner, "three", "456", slot=1)
        new_two = reserve(owner, "four", "789", "other", slot=2)
        new_one._room("456")
        new_two._room("789")
        status = owner.journal.status()
        assert [b["session"] for b in status["bindings"]] == [new_one.intent.session_id, new_two.intent.session_id]
        assert [t["session"] for t in status["tasks"]] == [first.intent.session_id, second.intent.session_id]
        assert [owner.journal.session(b.intent.session_id) for b in (first, second)] == original
        with pytest.raises(JournalConflict, match="capacity"):
            reserve(owner, "five", "900", "third")


def test_same_room_and_native_path_alias_reject_before_capture_side_effects(tmp_path):
    data = local_media(tmp_path / "fixture.flv")
    with authority(tmp_path) as owner:
        old = reserve(owner)
        old.run(**observations(data))
        before = contents(owner.root)
        for name, room, creator in (("alias", "123", "other"), ("ONE", "456", "creator")):
            with pytest.raises(JournalConflict):
                reserve(owner, name, room, creator)
        assert contents(owner.root) == before
        assert len(owner.journal.status()["units"]) == 1


def test_stop_before_admission_and_cooperative_stop_have_distinct_dispositions(tmp_path):
    data = local_media(tmp_path / "fixture.flv")
    with authority(tmp_path) as owner:
        absent = reserve(owner, raw=False)
        absent.stop()
        def forbidden(*_args):
            raise AssertionError("stopped reservation opened source")
        result = absent.run(resolver=forbidden)
        assert result.phase == "no_assembly" and not Path(absent.intent.parts_path).exists()
        assert not owner.journal.status()["units"]
        stopped = reserve(owner, "stopped", "456")
        def source(_, raw):
            raw.write(data)
            tags = iter_tags((data,))
            for index, tag in enumerate(tags):
                yield tag
                if index == 10:
                    stopped.stop()
        from tikrec.source import iter_tags
        result = stopped.run(**observations(data, "456", source=source))
        assert result.phase == "queued" and manifest(stopped)["interrupted"]
        row = owner.journal.session(stopped.intent.session_id)
        assert row["stop"] == 1 and row["recovery"] == "user_stop"


def test_closed_input_handles_hold_and_notification_loss_keeps_queue(tmp_path):
    data = local_media(tmp_path / "fixture.flv")
    with authority(tmp_path) as owner:
        old = reserve(owner)
        def check(boundary):
            if boundary == "confirmed_h":
                with pytest.raises(OSError):
                    Path(old.intent.parts_path, "part-0001.flv").open("ab")
        old._fault = check
        def notify(_):
            raise OSError("projection lost")
        result = old.run(notify=notify, **observations(data))
        assert result.notification_error and result.phase == "queued"
        assert owner.journal.session(old.intent.session_id)["task"]["state"] == "queued"
        reserve(owner, "two", "456")


def test_writer_still_open_refuses_seal_and_retains_binding(tmp_path):
    data = local_media(tmp_path / "fixture.flv")
    with authority(tmp_path) as owner:
        bridge = reserve(owner)
        handles = []
        def retain(boundary):
            if boundary == "before_inventory":
                handles.append(Path(bridge.intent.parts_path, "part-0001.flv").open("rb"))
        bridge._fault = retain
        try:
            with pytest.raises(CaptureHandoffError):
                bridge.run(**observations(data))
            row = owner.journal.session(bridge.intent.session_id)
            assert row["phase"] == "closing" and row["task"] is None and row["seal"] is None
            assert row["recovery"] == "ambiguous_state"
            assert any(b["session"] == bridge.intent.session_id for b in owner.journal.status()["bindings"])
        finally:
            for handle in handles:
                handle.close()


def test_eight_real_outstanding_captures_transfer_reserved_units_without_overflow(tmp_path):
    data = local_media(tmp_path / "fixture.flv")
    with authority(tmp_path) as owner:
        old = []
        for index in range(6):
            bridge = reserve(owner, f"old{index}", str(index + 1), f"creator{index}", raw=False)
            bridge.run(**observations(data, str(index + 1)))
            old.append(bridge.intent.session_id)
        new = (reserve(owner, "seven", "7", "seventh"), reserve(owner, "eight", "8", "eighth"))
        assert len(owner.journal.status()["units"]) == 8
        for bridge, room in zip(new, ("7", "8")):
            bridge.run(**observations(data, room))
            assert len(owner.journal.status()["units"]) == 8
        status = owner.journal.status()
        assert [t["session"] for t in status["tasks"]] == old + [b.intent.session_id for b in new]
        assert all(b["session"] is None for b in status["bindings"])
        with pytest.raises(JournalConflict, match="work limit"):
            reserve(owner, "ninth", "9", "ninth")
