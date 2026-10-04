"""Durable sequential read-only FFprobe and unchanged actual sealed fixture bytes."""

import os
import json
import hashlib
import pytest
import shutil
import subprocess
from pathlib import Path

from tests.sealed_input_helpers import sealed, hashes
from tests.owned_process_helpers import managed_process
from tests.test_attempt_coordinator_faults import factory
from tikrec.attempt_coordinator import AttemptCoordinator
from tikrec.part_validation import validate_part


pytestmark = pytest.mark.skipif(os.name != "nt", reason="real Windows capture and native input proof")


def test_owned_ffprobe_declared_records_and_unchanged_h_evidence(sealed, managed_process):
    owner, bridge, original = sealed
    before = hashes(owner.root)
    source = owner.root.parent / "source.flv"
    source_before = source.read_bytes()
    tables = ["sessions", "bindings", "units", "artifacts", "rooms", "attempts", "tasks",
              "queue_entries", "automatic_receipts", "operations", "attempt_owners", "child_launches"]
    def snapshot():
        return owner.journal._read(lambda connection: {table: [dict(row) for row in connection.execute(
            "SELECT * FROM " + table)] for table in tables})
    original_tables = snapshot()
    runner = AttemptCoordinator(owner, process_factory=factory(managed_process))
    runner.claim()
    executable = Path(shutil.which("ffprobe")).resolve()
    results = []
    def run(command, **_):
        evidence = runner.run_child(executable, command[1:], cwd=owner.root.parent, phase="probe", timeout=20)
        assert evidence.stream_status == ("complete", "complete") and evidence.active_processes == 0
        assert evidence.truncated == (0, 0) and evidence.error is None
        results.append(evidence)
        return subprocess.CompletedProcess(command, 0, evidence.stdout.decode(), evidence.stderr.decode())
    try:
        for part in runner.guard.revalidate().flv_inputs:
            problems, warnings = validate_part(part, str(executable), run)
            assert not problems and not warnings
        assert len(results) == 2
        row = owner.journal.session(bridge.intent.session_id)
        assert row["seal"] == original["seal"] and row["phase"] == "running"
        assert row["artifacts"] == original["artifacts"] and row["rooms"] == original["rooms"]
        assert len(owner.journal.status()["units"]) == 1
        assert hashes(owner.root) == before and source.read_bytes() == source_before
        assert not Path(bridge.intent.output_path).exists()
        record = owner.journal.owned_attempt(runner.token)
        assert record["sequence"] == 2 and record["child"]["cleanup"] == 1
        changed = snapshot()
        for table in ("bindings", "units", "artifacts", "rooms", "queue_entries", "automatic_receipts"):
            assert changed[table] == original_tables[table]
        assert changed["sessions"] == [{**original_tables["sessions"][0], "phase": "running",
                                      "revision": original_tables["sessions"][0]["revision"] + 1}]
        assert changed["tasks"] == [{**original_tables["tasks"][0], "state": "running",
            "revision": 2, "attempt": 1, "token": runner.token}]
        assert changed["attempts"] == [{"token": runner.token, "session": bridge.intent.session_id,
                                      "number": 1, "state": "running", "proof": None}]
        assert changed["operations"][:len(original_tables["operations"])] == original_tables["operations"]
        assert [r["kind"] for r in changed["operations"][len(original_tables["operations"]):]] == [
            "claim_owned", "bind_owned_inputs", *(["launch_intent", "child_identity", "child_exit",
                "child_diagnostics", "child_cleanup"] * 2)]
        (owner.root.parent / "durable-reader-evidence.json").write_text(json.dumps({
            "before": before, "source_sha256": hashlib.sha256(source_before).hexdigest(),
            "unchanged": True, "token": runner.token,
            "owned": record, "validation": "part decode and packet DTS passed"}, indent=2))
    finally:
        assert runner.close()
