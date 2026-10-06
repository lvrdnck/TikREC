"""New full-lifecycle child failure/descendant/unknown lifetime cases retain capacity."""
import os
import time
from threading import Thread, Event
from pathlib import Path
import pytest
from tests.journal_settlement_helpers import settling, adapter_for, independent_cleanup
from tests.journal_assembly_helpers import managed_process
from tests.test_journal_assembly_lifetime import launch
from tests.journal_validation_native_helpers import native_validator
from tests.owned_process_helpers import Events
from tests.capture_handoff_helpers import reserve, observations
from tikrec.journal_settlement import SettlementError
pytestmark = pytest.mark.skipif(os.name != 'nt', reason='Windows connected lifecycle')


@pytest.mark.parametrize("mode", ["diagnostic", "nonzero", "utf8", "unknown", "descendant"])
def test_new_success_path_retains_failed_or_unknown_validator(settling, monkeypatch, mode):
    adapter, _, _, _, _ = settling
    runner = adapter.coordinator
    with Events() as barrier:
        adapter.manifest.publication.validation.assembly.ffprobe = native_validator(runner.authority.root.parent / "validator", mode, barrier.names)
        def unavailable(*_):
            raise OSError("native lifetime unavailable")
        def fault(point):
            if point == "native_after_resume" and runner.children[-1]["intent"].get("validation_index") == 1 and mode == "unknown":
                native = runner.children[-1]["process"].native
                monkeypatch.setattr(native, "status", unavailable)
                monkeypatch.setattr(native, "terminate", unavailable)
        runner._fault = fault
        worker, results = launch(adapter)
        try:
            if mode == "descendant":
                barrier.wait()
                deadline = time.monotonic() + 10
                process = runner.children[-1]["process"]
                while process.evidence().root_exit_code is None:
                    assert time.monotonic() < deadline
                    time.sleep(0.005)
                assert process.evidence().active_processes >= 1
                assert runner.journal.owned_attempt(runner.token)["child"]["exit"] is None
                adapter.cancel()
            worker.join(20)
            assert not worker.is_alive()
            assert isinstance(results[0], SettlementError)
            assert runner.journal.publication(runner.token) is None
            assert not adapter.close(0) and not runner.guard.closed
        finally:
            barrier.release()
            worker.join(15)


def test_prepared_release_keeps_disjoint_captures_available_and_next_fifo_safe(settling, managed_process):
    import sys
    adapter, _, _, _, _ = settling
    runner, ready, release = adapter.coordinator, Event(), Event()
    def fault(point):
        if point == 'after_release_preparation':
            ready.set()
            assert release.wait(15)
    runner._fault = fault
    with Events() as unrelated:
        other = managed_process()
        other.start(Path(sys._base_executable), ['-m', 'tests.owned_process_probe', 'leaf',
            str(runner.authority.root.parent), *unrelated.names], cwd=runner.authority.root.parent,
            before_resume=lambda identity: identity)
        unrelated.wait()
        worker, results = launch(adapter)
        try:
            assert ready.wait(15)
            captures = [reserve(runner.authority, 'two', room='234', creator='c2'),
                        reserve(runner.authority, 'three', room='345', creator='c3')]
            assert sum(b['session'] is not None for b in runner.journal.status()['bindings']) == 2
            data = (runner.authority.root.parent / 'one-source1.flv').read_bytes()
            for capture, room in zip(captures, ('234', '345'), strict=True):
                assert capture.run(**observations(data, room=room)).phase == 'queued'
            assert len(runner.journal.status()['units']) == 3
            assert other.poll().state == 'running'
        finally:
            release.set()
            worker.join(20)
            assert not worker.is_alive()
            unrelated.release()
            assert other.wait(10).root_exit_code == 0
        assert results[0]['state'] == 'released'
        assert len(runner.journal.status()['units']) == 2
        for capture in captures:
            successor = adapter_for(runner.authority, managed_process)
            try:
                assert successor.run()['session_id'] == capture.intent.session_id
            finally:
                independent_cleanup(successor)
        assert not runner.journal.status()['units']


