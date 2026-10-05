"""Independent disposable cleanup for scratch integration fault fixtures."""

import sys
import json
import hashlib
from pathlib import Path

import pytest

from tests.owned_process_helpers import managed_process
from tests.sealed_input_helpers import sealed
from tikrec.attempt_coordinator import AttemptCoordinator


@pytest.fixture
def scratch_runner(sealed, managed_process, monkeypatch):
    """Retain all exact scratch owners until assertions finish, then release test pins."""
    owner, _, _ = sealed
    originals = {str(path): hashlib.sha256(path.read_bytes()).hexdigest()
                 for path in owner.root.rglob("*") if path.is_file()
                 and path.name != ".tikrec-lifecycle.lock"}
    unrelated = owner.root.parent / "unrelated-sentinel.bin"
    unrelated.write_bytes(b"separate fixture bytes must stay unchanged")
    unrelated_hash = hashlib.sha256(unrelated.read_bytes()).hexdigest()
    committed = sealed[2]
    def create(sid, token):
        process = managed_process()
        process.session_id, process.attempt_token = sid, token
        return process
    runner = AttemptCoordinator(owner, process_factory=create)
    runner.claim()
    yield runner
    monkeypatch.undo()
    runner._fault = lambda _: None
    owner.journal._fault = None
    runner.close()
    current = {name: hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in originals}
    assert current == originals
    assert hashlib.sha256(unrelated.read_bytes()).hexdigest() == unrelated_hash
    session = owner.journal.session(committed["id"])
    for field in ("seal", "seal_hash", "artifacts", "rooms"):
        assert session[field] == committed[field]
    (owner.root.parent / "scratch-integration-evidence.json").write_text(json.dumps({
        "original_hashes": originals, "unchanged": current == originals,
        "unrelated_hash": unrelated_hash,
        "owned": owner.journal.owned_attempt(runner.token),
        "cleanup": runner.cleanup_evidence()}, indent=2), encoding="utf-8")
    # This independent cleanup is permitted only for disposable fixtures after
    # exact child exit; production deliberately retains failed scratch owners.
    assert all(child["process"].closed and child["process"].evidence().state in
               {"not_created", "confirmed_exited"} for child in runner.children)
    if runner.scratch is not None:
        for held in [*runner.scratch.artifacts.values(), runner.scratch.workspace]:
            if held is not None:
                held.close()
    runner.close()


def write_candidate(runner, *, helpers=()):
    """Run a real contained synthetic writer with deliberately varied helper ordering."""
    scratch = runner.reserve_scratch(helpers=helpers)
    names = ("candidate.mp4", *helpers)
    code = "from pathlib import Path;" + ";".join(
        "Path(" + repr(name) + ").write_bytes(" + repr(name.encode()) + ")" for name in names)
    scratch.run_writer(Path(sys._base_executable), ["-c", code], timeout=10,
                       outputs=tuple(reversed(names)))
    return scratch, runner.children[-1]["launch"]
