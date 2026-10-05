"""R8–R10 source-review regressions reproduced with disposable native objects."""

import os
import sys
from pathlib import Path

import pytest

from tests.attempt_scratch_helpers import scratch_runner, write_candidate, sealed, managed_process
from tikrec.attempt_coordinator import AttemptError
from tikrec.attempt_scratch import ScratchHandle


pytestmark = pytest.mark.skipif(os.name != "nt", reason="actual Windows scratch objects")


def test_writer_first_failure_survives_unavailable_hold_lookup(scratch_runner, monkeypatch):
    runner = scratch_runner
    scratch = runner.reserve_scratch()
    original = ValueError("original writer failure")
    def boundary(point):
        if point == "after_identity":
            raise original
    def unavailable(_):
        raise OSError("scratch journal lookup unavailable")
    runner._fault = boundary
    monkeypatch.setattr(runner.journal, "scratch", unavailable)
    with pytest.raises(AttemptError) as caught:
        scratch.run_writer(Path(sys._base_executable), ["-c", "print('writer')"], timeout=10)
    assert caught.value.original.original is original
    assert caught.value.coordinator is runner and runner.scratch is scratch
    assert scratch.failure is caught.value.original and runner.cancelled.is_set()
    assert any("lookup unavailable" in str(error) for error in runner.errors)
    assert len(runner.children) == 1 and runner.children[0]["process"].closed


def test_seal_first_failure_survives_unavailable_hold_lookup(scratch_runner, monkeypatch):
    runner = scratch_runner
    scratch, launch = write_candidate(runner)
    original = ValueError("original hash failure")
    def failed_hash(_):
        raise original
    def unavailable(_):
        raise OSError("scratch journal lookup unavailable")
    monkeypatch.setattr(scratch, "_hash", failed_hash)
    monkeypatch.setattr(runner.journal, "scratch", unavailable)
    with pytest.raises(ValueError) as caught:
        scratch.seal_candidate(launch)
    assert caught.value is original and scratch.failure is original
    assert scratch.artifacts["candidate.mp4"].handle is not None
    assert any("lookup unavailable" in str(error) for error in runner.errors)


def test_partial_native_artifact_owner_is_explicitly_registered(scratch_runner, monkeypatch):
    runner = scratch_runner
    scratch, launch = write_candidate(runner)
    opened = []
    native_close = ScratchHandle.close
    native_identity = ScratchHandle._path_identity
    original = ValueError("artifact proof failed after native open")
    def failed_identity(self):
        if self.path.name == "candidate.mp4":
            raise original
        return native_identity(self)
    def failed_close(self):
        opened.append(self)
        raise OSError("artifact native close unconfirmed")
    with monkeypatch.context() as patch:
        patch.setattr(ScratchHandle, "_path_identity", failed_identity)
        patch.setattr(ScratchHandle, "close", failed_close)
        try:
            with pytest.raises(ValueError) as caught:
                scratch.seal_candidate(launch)
            assert caught.value is original
            assert scratch.artifacts["candidate.mp4"] is opened[0]
            assert opened[0].handle is not None
            assert any("close unconfirmed" in str(error) for error in runner.errors)
        finally:
            # The independent test reference also cleans the unchanged-code
            # regression, whose failed constructor lacks an explicit registry.
            for held in opened:
                native_close(held)


def test_retained_bound_scratch_is_not_successful_cleanup(scratch_runner):
    runner = scratch_runner
    scratch = runner.reserve_scratch()
    assert not runner.close()
    assert runner.cancelled.is_set() and not runner.closed
    assert scratch.workspace.handle is not None
    assert runner.journal.scratch(runner.token)["state"] == "held"


def test_after_artifact_bind_addition_prevents_candidate_ready(scratch_runner):
    runner = scratch_runner
    scratch, launch = write_candidate(runner)
    unexpected = scratch.path / "unexpected.txt"
    def boundary(point):
        if point == "after_artifact_bind":
            unexpected.write_bytes(b"unexplained")
    runner._fault = boundary
    with pytest.raises(Exception):
        scratch.seal_candidate(launch)
    assert unexpected.read_bytes() == b"unexplained"
    assert not scratch.candidate_ready
    record = runner.journal.scratch(runner.token)
    assert record["state"] == "held" and record["candidate"] is None
