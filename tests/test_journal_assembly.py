"""The connected adapter claims one FIFO task and seals only unpublished evidence."""

import os
from pathlib import Path

import pytest

from tests.journal_assembly_helpers import connected, managed_process, queue_media
from tests.capture_handoff_helpers import authority
from tikrec.journal_assembly import JournalAssembly

pytestmark = pytest.mark.skipif(os.name != "nt", reason="real Windows journal assembly")


def test_single_fifo_claim_and_same_attempt_scratch(connected):
    adapter, bridge, original, _ = connected
    owner = adapter.coordinator.authority
    second, _ = queue_media(owner, owner.root.parent, name="two", room="234")
    result = adapter.run()
    assert result.state == "candidate_ready" and result.session_id == bridge.intent.session_id
    assert result.publication == "unpublished" and result.media_validation == "not_checked"
    assert result.plan.stream_copy and result.diagnostics_complete
    runner = adapter.coordinator
    assert result.attempt_token == runner.token
    scratch = owner.journal.scratch(runner.token)
    assert scratch["candidate"]["seal_hash"] == original["seal_hash"]
    assert scratch["candidate"]["execution"]["input_decode"] == "unknown"
    assert {p.name for p in result.work_scope.iterdir()} == {"candidate.mp4", "concat.ffconcat"}
    assert len(runner.children) == 1
    intent = runner.children[0]["intent"]
    assert intent["access"] == "write" and intent["cwd"] == str(result.work_scope)
    assert set(intent["outputs"]) == {"candidate.mp4", "concat.ffconcat"}
    assert "-I" in intent["arguments"] and "concat.ffconcat" in intent["arguments"][-1]
    assert owner.journal.session(second.intent.session_id)["phase"] == "queued"
    assert owner.journal.session(original["id"])["phase"] == "running"
    assert len(owner.journal.status()["units"]) == 2
    with pytest.raises(ValueError, match="single-use"):
        adapter.run()
    assert adapter.close()
    assert owner.journal.session(original["id"])["phase"] == "running"
    assert len(owner.journal.status()["units"]) == 2
    assert not Path(bridge.intent.output_path).exists()


def test_empty_explicit_authority_is_single_use_without_scratch_or_execution(tmp_path):
    executable = tmp_path / "never-launched.exe"
    executable.write_bytes(b"empty queue fixture executable")
    with authority(tmp_path) as owner:
        adapter = JournalAssembly(owner, ffmpeg=executable, ffprobe=executable)
        assert adapter.run() is None
        assert not adapter.coordinator.children and adapter.coordinator.scratch is None
        assert not owner.journal.status()["units"]
        with pytest.raises(ValueError, match="single-use"):
            adapter.run()
        assert adapter.close()
