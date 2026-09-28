"""Policy publication and irreversible removal have one serialization boundary."""

import argparse
import io
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

import pytest

from tests.test_retention_execute import events, fixture
from tikrec.retention_cli import run_retention_command
from tikrec.retention_windows import HeldArtifact


@pytest.mark.parametrize("change", ["protect", "age", "disabled"])
@pytest.mark.parametrize("position", [1, 2])
def test_policy_becomes_effective_after_proof_before_removal(
        tmp_path, monkeypatch, change, position):
    root, _, _, store, _, audit, run = fixture(tmp_path)
    prove, calls = HeldArtifact.prove, 0

    def update_after_proof(self, digest):
        nonlocal calls
        prove(self, digest)
        calls += 1
        if calls == position:
            if change == "protect":
                run_retention_command(argparse.Namespace(
                    config_path=str(store.path), retention_action="protect", creator="alpha"),
                    io.StringIO())
            else:
                store.save(replace(store.load(), retention_max_age_days=(
                    100 if change == "age" else None)))

    monkeypatch.setattr(HeldArtifact, "prove", update_after_proof)
    with pytest.raises(ValueError, match="policy"):
        run()
    records = events(audit)
    assert sum(record["event"] == "deleted" for record in records) == position - 1
    assert records[-1]["event"] == "failed"
    assert (root / records[0]["quarantine_order"][position - 1]).exists()
    assert (root / "alpha.mp4").exists()


def test_concurrent_protection_waits_for_current_removal_then_stops_next(
        tmp_path, monkeypatch):
    root, _, _, store, _, audit, run = fixture(tmp_path)
    delete = HeldArtifact.delete
    started, committed = threading.Event(), threading.Event()
    sequence, futures = [], []

    def protect():
        started.set()
        store.save(replace(store.load(), retention_protected_creators=("alpha",)))
        sequence.append("protected")
        committed.set()

    with ThreadPoolExecutor() as pool:
        def during_removal(self):
            if not futures:
                futures.append(pool.submit(protect))
                assert started.wait(2) and not committed.wait(0.1)
                assert not store.load().retention_protected_creators
            delete(self)
            sequence.append("removed")

        def next_artifact(_path):
            if futures:
                futures[0].result(timeout=3)

        monkeypatch.setattr(HeldArtifact, "delete", during_removal)
        with pytest.raises(ValueError, match="policy"):
            run(before_mutation=next_artifact)
    assert sequence == ["removed", "protected"]
    assert sum(record["event"] == "deleted" for record in events(audit)) == 1
    assert events(audit)[-1]["event"] == "failed"
    assert (root / "alpha.mp4").exists()


def test_unrelated_config_write_during_byte_proof_does_not_block(tmp_path, monkeypatch):
    _, _, _, store, _, audit, run = fixture(tmp_path)
    prove = HeldArtifact.prove
    with ThreadPoolExecutor() as pool:
        def update(self, digest):
            prove(self, digest)
            pool.submit(store.update, lambda current: replace(
                current, debug_tracebacks=True)).result(timeout=3)

        monkeypatch.setattr(HeldArtifact, "prove", update)
        run()
    assert events(audit)[-1]["event"] == "completed"
    assert store.load().effective_debug_tracebacks
