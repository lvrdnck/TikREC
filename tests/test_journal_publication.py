"""Publication must use only the live same-attempt candidate and never settle it."""

import json
import os
from pathlib import Path

import pytest

from tests.journal_publication_helpers import publishing, held_hash
from tests.journal_assembly_helpers import managed_process

pytestmark = pytest.mark.skipif(os.name != "nt", reason="native Windows publication")


@pytest.mark.parametrize("publishing", [False, True], indirect=True, ids=["copy", "libx264"])
def test_connected_publication_keeps_exact_validated_identity_and_all_pins(publishing):
    adapter, bridge, original, before = publishing
    result = adapter.run()
    runner = adapter.coordinator
    record = runner.journal.publication(runner.token)
    candidate = runner.journal.scratch(runner.token)["candidate"]
    held = runner.scratch.artifacts["candidate.mp4"]
    assert result == record["evidence"]
    assert result["state"] == "observed_published"
    assert held.path == Path(bridge.intent.output_path) and held.path.exists()
    assert not (runner.scratch.path / "candidate.mp4").exists()
    assert held.stamp == candidate["stamp"] and held_hash(held) == candidate["sha256"]
    assert result["identity"] == json.loads(json.dumps(bridge.intent.output.__dict__))
    assert candidate["publication"] == "unpublished" and candidate["validation"] == "not_checked"
    assert runner.journal.validation(runner.token)["evidence"]["report"]["passed"]
    assert runner.guard.closed is False and not adapter.close()
    assert held.handle is not None and runner.scratch.workspace.handle is not None
    with pytest.raises(Exception):
        adapter.run()
    with pytest.raises(Exception):
        adapter.capability.promote()
    (runner.authority.root.parent / "publication-media-evidence.json").write_text(
        json.dumps({"record": record, "candidate": candidate, "hashes": before,
                    "pins": runner.journal.status(), "unchanged": True}, indent=2))


def test_collision_at_native_boundary_is_untouched(publishing):
    adapter, bridge, _, _ = publishing
    def fault(point):
        if point == "before_publication_fence":
            Path(bridge.intent.output_path).write_bytes(b"late destination must survive")
    adapter.coordinator._fault = fault
    with pytest.raises(Exception):
        adapter.run()
    assert Path(bridge.intent.output_path).read_bytes() == b"late destination must survive"
    record = adapter.coordinator.journal.publication(adapter.coordinator.token)
    assert record is not None and record["evidence"] is None
    assert (adapter.coordinator.scratch.path / "candidate.mp4").exists()
