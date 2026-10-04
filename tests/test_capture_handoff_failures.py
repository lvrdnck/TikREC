"""Real capture closure failure boundaries retain exactly one responsibility."""

import os
from pathlib import Path

import pytest

from tests.capture_handoff_helpers import authority, local_media, manifest, observations, reserve
from tikrec.capture_handoff import CaptureHandoffError
from tikrec.session_journal_types import JournalError

pytestmark = pytest.mark.skipif(os.name != "nt", reason="requires native Windows failure boundaries")


def retained(owner, bridge):
    """Assert no invented seal/task or MP4 completion after failed capture close."""
    row = owner.journal.session(bridge.intent.session_id)
    assert row["phase"] == "closing" and row["seal"] is None and row["task"] is None
    assert row["recovery"] == "ambiguous_state"
    assert owner.journal.status()["units"] == [{"session": bridge.intent.session_id, "kind": "capture"}]
    assert any(b["session"] == bridge.intent.session_id for b in owner.journal.status()["bindings"])
    assert manifest(bridge)["finalization"]["status"] != "completed"


@pytest.mark.parametrize("boundary", ["flush_flv", "flush_manifest", "flush_connections",
                                      "before_marker", "after_marker"])
def test_mandatory_flush_and_marker_boundaries_keep_capture_owner(tmp_path, boundary):
    data = local_media(tmp_path / "fixture.flv")
    with authority(tmp_path) as owner:
        bridge = reserve(owner)
        def fail(name):
            if name == boundary:
                raise OSError(boundary)
        bridge._fault = fail
        with pytest.raises(CaptureHandoffError):
            bridge.run(**observations(data))
        retained(owner, bridge)


@pytest.mark.parametrize("boundary", ["after_begin", "after_seal", "after_queue_entry", "after_task",
                                      "after_transfer", "after_release", "after_writes", "before_commit"])
def test_H_rollbacks_leave_marker_capture_binding_and_no_task(tmp_path, boundary):
    data = local_media(tmp_path / "fixture.flv")
    with authority(tmp_path) as owner:
        bridge = reserve(owner)
        def fail(kind, name):
            if kind == "handoff" and name == boundary:
                raise OSError(boundary)
        owner.journal._fault = fail
        with pytest.raises(CaptureHandoffError):
            bridge.run(**observations(data))
        retained(owner, bridge)
        assert owner.inspect(bridge.intent.session_id)["phase"] == "closing"


@pytest.mark.parametrize("target", ["writer_close", "connection_log", "manifest", "marker_write"])
def test_real_close_and_control_write_failures_keep_artifacts(tmp_path, monkeypatch, target):
    data = local_media(tmp_path / "fixture.flv")
    with authority(tmp_path) as owner:
        bridge = reserve(owner)
        if target == "writer_close":
            import tikrec.writer as module
            original = module._close_part
            def fail(*args):
                original(*args)
                if args[0] is not None:
                    raise OSError("writer close failed")
            monkeypatch.setattr(module, "_close_part", fail)
        elif target == "connection_log":
            import tikrec.live_session as module
            def fail(*_):
                raise OSError("connection log fsync failed")
            monkeypatch.setattr(module, "append_connection_record", fail)
        elif target == "manifest":
            import tikrec.manifest as module
            original = module.write_manifest
            def fail(path, values, **kwargs):
                if values["ended_at"] is not None:
                    raise OSError("terminal manifest failed")
                original(path, values, **kwargs)
            monkeypatch.setattr(module, "write_manifest", fail)
        else:
            import tikrec.capture_handoff as module
            def fail(path, values):
                Path(path).write_bytes(b'{"incomplete":')
                raise OSError("marker fsync failed")
            monkeypatch.setattr(module, "persist_marker", fail)
        with pytest.raises(CaptureHandoffError):
            bridge.run(**observations(data))
        retained(owner, bridge)
        assert Path(bridge.intent.parts_path, "part-0001.flv").exists()


def test_original_source_failure_survives_secondary_close_and_connection_failure(tmp_path, monkeypatch):
    from tikrec.flv import FlvFormatError
    import tikrec.live_session as module
    with authority(tmp_path) as owner:
        bridge = reserve(owner)
        original = FlvFormatError("source framing failed")
        class Source:
            def __iter__(self):
                return self
            def __next__(self):
                raise original
            def close(self):
                raise OSError("secondary source close failed")
        def append_failure(*_):
            raise OSError("secondary connection write failed")
        monkeypatch.setattr(module, "append_connection_record", append_failure)
        opts = observations(b"", source=lambda *_: Source())
        with pytest.raises(CaptureHandoffError) as caught:
            bridge.run(**opts)
        assert caught.value.original is original
        assert len(caught.value.cleanup_errors) >= 2
        assert owner.journal.session(bridge.intent.session_id)["seal"] is None


@pytest.mark.parametrize("really_closed", [False, True])
def test_raw_close_warning_is_optional_only_if_native_handle_closure_is_proved(tmp_path, really_closed):
    data = local_media(tmp_path / "fixture.flv")
    keepers = []
    with authority(tmp_path) as owner:
        bridge = reserve(owner)
        opts = observations(data)
        original = opts["raw_tag_source"]
        def source(url, raw):
            actual = raw.raw._handle
            keepers.append(actual)
            class BadClose:
                def write(self, data):
                    return actual.write(data)
                def close(self):
                    if really_closed:
                        actual.close()
                    raise OSError("raw close warning")
            raw.raw._handle = BadClose()
            yield from original(url, raw)
        opts["raw_tag_source"] = source
        try:
            if really_closed:
                assert bridge.run(**opts).phase == "queued"
                assert "raw_warning" in owner.journal.session(bridge.intent.session_id)["seal"]["warnings"]
            else:
                with pytest.raises(CaptureHandoffError):
                    bridge.run(**opts)
                retained(owner, bridge)
        finally:
            for actual in keepers:
                actual.close()


def test_commit_with_unavailable_receipt_blocks_capacity_until_explicit_reconciliation(tmp_path, monkeypatch):
    data = local_media(tmp_path / "fixture.flv")
    with authority(tmp_path) as owner:
        bridge = reserve(owner)
        def fault(kind, boundary):
            if kind == "handoff" and boundary == "after_commit":
                raise OSError("lost ack")
        owner.journal._fault = fault
        original = owner.journal.operation
        def unavailable(_):
            raise OSError("receipt temporarily unavailable")
        monkeypatch.setattr(owner.journal, "operation", unavailable)
        with pytest.raises(CaptureHandoffError):
            bridge.run(**observations(data))
        assert owner.journal.session(bridge.intent.session_id)["phase"] == "queued"
        with pytest.raises(JournalError, match="unreconciled"):
            reserve(owner, "two", "456")
        monkeypatch.setattr(owner.journal, "operation", original)
        assert owner.inspect(bridge.intent.session_id)["phase"] == "queued"
        reserve(owner, "two", "456")


@pytest.mark.parametrize("role", ["raw", "arrivals"])
def test_optional_diagnostic_flush_warning_does_not_block_closed_media(tmp_path, role):
    data = local_media(tmp_path / "fixture.flv")
    with authority(tmp_path) as owner:
        bridge = reserve(owner)
        def fault(boundary):
            if boundary == "flush_" + role:
                raise OSError("optional durable raw flush failed")
        bridge._fault = fault
        assert bridge.run(**observations(data)).phase == "queued"
        assert "raw_flush_failed" in owner.journal.session(bridge.intent.session_id)["seal"]["warnings"]
