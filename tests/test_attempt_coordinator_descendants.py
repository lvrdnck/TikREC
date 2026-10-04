"""Whole-job gating and untouched unrelated processes through the coordinator."""

import os
import sys
import time
from pathlib import Path
from threading import Thread

import pytest

from tests.sealed_input_helpers import sealed
from tests.owned_process_helpers import Events, managed_process
from tests.test_attempt_coordinator_faults import factory
from tikrec.attempt_coordinator import AttemptCoordinator
from tikrec.session_journal_types import JournalError

pytestmark = pytest.mark.skipif(os.name != "nt", reason="Windows descendant jobs")


def test_root_exit_cannot_record_exit_or_start_successor_while_descendant_runs(sealed, managed_process):
    owner, _, _ = sealed
    runner = AttemptCoordinator(owner, process_factory=factory(managed_process))
    runner.claim()
    results, errors = [], []
    with Events() as leaf, Events() as root, Events() as unrelated:
        other = managed_process()
        other.start(Path(sys._base_executable), ["-m", "tests.owned_process_probe", "leaf",
            str(owner.root.parent), *unrelated.names], cwd=owner.root.parent, before_resume=lambda value: value)
        unrelated.wait()
        def launch():
            try:
                results.append(runner.run_child(Path(sys._base_executable), ["-m", "tests.owned_process_probe",
                    "tree", str(owner.root.parent), *leaf.names, root.names[1]],
                    cwd=owner.root.parent, phase="probe", timeout=15))
            except BaseException as error:
                errors.append(error)
        thread = Thread(target=launch)
        thread.start()
        try:
            leaf.wait()
            root.release()
            process = runner.children[0]["process"]
            deadline = time.monotonic() + 10
            while process.evidence().root_exit_code is None:
                assert time.monotonic() < deadline
                time.sleep(0.005)
            evidence = process.evidence()
            assert evidence.active_processes >= 1 and evidence.state == "running"
            row = owner.journal.owned_attempt(runner.token)
            assert row["child"]["exit"] is None
            intent = {**row["child"]["intent"], "predecessor": row["child"]["id"]}
            with pytest.raises(JournalError):
                owner.journal.launch_intent(runner.uuid(), runner.token, runner.owner,
                    row["revision"], runner.uuid(), intent)
            runner.cancel(5)
            assert other.poll().state == "running" and other.evidence().active_processes >= 1
        finally:
            leaf.release()
            root.release()
            unrelated.release()
            thread.join(20)
            assert not thread.is_alive()
            assert other.wait(10).root_exit_code == 0
            assert runner.close()
        child = owner.journal.owned_attempt(runner.token)["child"]
        assert child["exit"]["active"] == 0 and child["cleanup"] == 1
        assert len(runner.children) == 1
