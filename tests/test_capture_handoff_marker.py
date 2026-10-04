"""Pending marker is a retained pin; only the same catalog receipt proves H."""

import os
from pathlib import Path

import pytest

from tests.capture_handoff_helpers import authority, contents, local_media, observations, reserve
from tests.test_retention_plan import plan, session
from tikrec.capture_handoff import CaptureHandoffError
from tikrec.capture_handoff_marker import MARKER_NAME
from tikrec.session_journal_types import JournalError

pytestmark = pytest.mark.skipif(os.name != "nt", reason="requires native Windows pending marker")


def test_marker_alone_retains_capture_and_is_not_an_authority_to_resume(tmp_path):
    data = local_media(tmp_path / "fixture.flv")
    with authority(tmp_path) as owner:
        bridge = reserve(owner)
        def fault(boundary):
            if boundary == "after_marker":
                raise OSError("before H")
        bridge._fault = fault
        with pytest.raises(CaptureHandoffError):
            bridge.run(**observations(data))
        assert Path(bridge.intent.parts_path, MARKER_NAME).exists()
        assert owner.inspect(bridge.intent.session_id) == {
            "session_id": bridge.intent.session_id, "phase": "closing",
            "operation": bridge.handoff_operation, "source_resume_allowed": False}
        assert owner.journal.session(bridge.intent.session_id)["task"] is None


def test_actual_queue_and_marker_cannot_become_retention_eligible(tmp_path):
    data = local_media(tmp_path / "fixture.flv")
    with authority(tmp_path) as owner:
        bridge = reserve(owner, raw=False)
        bridge.run(**observations(data))
        media_root = owner.root
        marker = Path(bridge.intent.parts_path, MARKER_NAME).read_bytes()
    before = contents(media_root)
    decisions = plan(media_root)
    assert decisions and all(d["classification"] != "eligible" for d in decisions)
    assert contents(media_root) == before
    # A separately completed fixture proves that the new filename itself also
    # trips today's conservative inventory guard, even with terminal output facts.
    complete = tmp_path / "retention-fixture"
    complete.mkdir()
    directory = session(complete, "completed")
    assert plan(complete)[0]["classification"] == "eligible"
    (directory / MARKER_NAME).write_bytes(marker)
    before = contents(complete)
    assert plan(complete)[0]["classification"] != "eligible"
    assert contents(complete) == before


def test_changed_marker_catalog_or_missing_marker_refuses_reconciliation(tmp_path):
    import json
    data = local_media(tmp_path / "fixture.flv")
    with authority(tmp_path) as owner:
        bridge = reserve(owner)
        bridge.run(**observations(data))
        path = Path(bridge.intent.parts_path, MARKER_NAME)
        original = path.read_bytes()
        values = json.loads(original)
        values["catalog_file"] = ["false", "authority"]
        path.write_text(json.dumps(values))
        with pytest.raises(JournalError, match="authority"):
            owner.inspect(bridge.intent.session_id)
        path.write_bytes(original)
        assert owner.inspect(bridge.intent.session_id)["phase"] == "queued"
        path.unlink()
        with pytest.raises(JournalError, match="lost its marker"):
            owner.inspect(bridge.intent.session_id)


@pytest.mark.parametrize("disposition", ["unsupported", None, False, [], {}])
def test_invalid_empty_marker_disposition_refuses_without_mutating_evidence(tmp_path, disposition):
    _assert_disposition_refusal(tmp_path, True, disposition)


@pytest.mark.parametrize("empty,disposition", [(False, "empty"), (True, "assembly")])
def test_marker_disposition_must_match_committed_seal_before_receipt_lookup(tmp_path, empty, disposition):
    _assert_disposition_refusal(tmp_path, empty, disposition)


def _assert_disposition_refusal(tmp_path, empty, disposition):
    import json
    data = local_media(tmp_path / "fixture.flv")
    with authority(tmp_path) as owner:
        bridge = reserve(owner, raw=False)
        options = observations(data)
        if empty:
            options["tag_source"] = lambda _: iter(())
        result = bridge.run(**options)
        path = Path(bridge.intent.parts_path, MARKER_NAME)
        original = path.read_bytes()
        values = json.loads(original)
        values["disposition"] = disposition
        path.write_text(json.dumps(values), encoding="utf-8")
        row, status = owner.journal.session(bridge.intent.session_id), owner.journal.status()
        before, state = contents(owner.root), contents(owner.journal.path.parent)
        original_lookup, looked_up = owner.journal.operation, []
        def lookup(operation):
            looked_up.append(operation)
            return original_lookup(operation)
        owner.journal.operation = lookup
        with pytest.raises(JournalError, match="disposition"):
            owner.inspect(bridge.intent.session_id)
        assert not looked_up
        assert owner.journal.session(bridge.intent.session_id) == row and owner.journal.status() == status
        assert contents(owner.root) == before and contents(owner.journal.path.parent) == state
        owner.journal.operation = original_lookup
        path.write_bytes(original)
        inspected = owner.inspect(bridge.intent.session_id)
        assert inspected["phase"] == result.phase and inspected["source_resume_allowed"] is False
