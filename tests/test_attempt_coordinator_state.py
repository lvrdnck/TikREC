"""Deterministic post-collection tails and durable phase evidence on real H fixtures."""

import os
import hashlib

import pytest

from tests.owned_process_state_helpers import state_owner
from tests.sealed_input_helpers import sealed
from tikrec.attempt_coordinator import AttemptCoordinator, AttemptError


pytestmark = pytest.mark.skipif(os.name != "nt", reason="real Windows capture and native input proof")


@pytest.mark.parametrize("stream", ["stdout", "stderr"])
def test_final_tail_and_prefix_drop_counts_survive_durable_exit(sealed, state_owner, stream):
    owner, _, _ = sealed
    process, executable = state_owner
    tail = b"final-tail" * 20000
    def factory(sid, token):
        process.session_id, process.attempt_token = sid, token
        def fault(point):
            if point == "after_create":
                process.native.tail = {stream: tail}
        process._fault = fault
        return process
    runner = AttemptCoordinator(owner, process_factory=factory)
    runner.claim()
    try:
        evidence = runner.run_child(executable, [], cwd=owner.root, phase="probe", timeout=1)
        assert getattr(evidence, stream) == tail[:5]
        assert evidence.truncated == ((len(tail)-5, 0) if stream == "stdout" else (0, len(tail)-5))
        child = owner.journal.owned_attempt(runner.token)["child"]
        assert child["exit"]["state"] == "confirmed_exited"
        assert child["diagnostics"]["complete"] and child["cleanup"] == 1
        assert child["diagnostics"]["counts"][stream] == len(tail)
        assert child["diagnostics"]["sha256"][stream] == hashlib.sha256(tail).hexdigest()
    finally:
        assert runner.close()


def test_eof_failure_keeps_durable_exit_separate(sealed, state_owner):
    owner, _, _ = sealed
    process, executable = state_owner
    def factory(sid, token):
        process.session_id, process.attempt_token = sid, token
        def fault(point):
            if point == "after_create":
                process.native.streams.no_eof = True
        process._fault = fault
        return process
    runner = AttemptCoordinator(owner, process_factory=factory)
    runner.claim()
    try:
        with pytest.raises(AttemptError):
            runner.run_child(executable, [], cwd=owner.root, phase="probe", timeout=0)
        child = owner.journal.owned_attempt(runner.token)["child"]
        assert child["exit"]["state"] == "confirmed_exited"
        assert not child["diagnostics"]["complete"]
        assert child["diagnostics"]["status"] == ["incomplete", "incomplete"]
        assert child["cleanup"] == 1
    finally:
        assert runner.close()
