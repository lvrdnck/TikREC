"""Deterministic native startup/cancellation/teardown orderings, exact-job cleanup."""

import os
import sys
from pathlib import Path
from threading import Event, Thread

import pytest

from tests.sealed_input_helpers import sealed
from tests.owned_process_helpers import managed_process
from tests.test_attempt_coordinator_faults import execute, factory
from tikrec.attempt_coordinator import AttemptCoordinator, AttemptError


pytestmark = pytest.mark.skipif(os.name != "nt", reason="real Windows capture and native input proof")


@pytest.mark.parametrize("boundary", ["after_launch_intent", "native_after_create", "after_identity",
                                     "before_resume_fence", "native_after_resume"])
def test_cancel_on_both_sides_of_authorization(sealed, managed_process, boundary):
    owner, _, _ = sealed
    ready, release = Event(), Event()
    failures = []
    def fault(point):
        if point == boundary:
            ready.set()
            assert release.wait(10), "startup barrier expired"
    runner = AttemptCoordinator(owner, process_factory=factory(managed_process), fault=fault)
    runner.claim()
    payload = owner.root.parent / "payload.txt"
    def launch():
        try:
            execute(runner, "from pathlib import Path;Path(" + repr(str(payload)) + ").write_text('ran')")
        except BaseException as error:
            failures.append(error)
    def cancel():
        try:
            runner.cancel(5)
        except BaseException as error:
            failures.append(error)
    launch_thread, cancel_thread = Thread(target=launch), Thread(target=cancel)
    launch_thread.start()
    try:
        assert ready.wait(10)
        cancel_thread.start()
        assert runner.cancelled.wait(5)
    finally:
        release.set()
        launch_thread.join(15)
        if cancel_thread.ident is not None:
            cancel_thread.join(15)
        assert not launch_thread.is_alive() and not cancel_thread.is_alive()
        runner._fault = lambda _: None
        assert runner.close()
    if boundary != "native_after_resume":
        assert not payload.exists()
    assert owner.journal.owned_attempt(runner.token)["state"] == "revoked"
    assert len(runner.children) == 1 and runner.children[0]["process"].closed
    threads = [Thread(target=runner.close) for _ in range(3)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(10)
        assert not thread.is_alive()


def test_unknown_lifetime_keeps_guard_and_owner_reachable(sealed, managed_process, monkeypatch):
    owner, _, _ = sealed
    originals = []
    def fault(point):
        if point == "native_after_resume":
            native = runner.children[-1]["process"].native
            originals.append((native, native.status, native.terminate))
            def unavailable():
                raise OSError("native lifetime unavailable")
            monkeypatch.setattr(native, "status", unavailable)
            monkeypatch.setattr(native, "terminate", unavailable)
    runner = AttemptCoordinator(owner, process_factory=factory(managed_process), fault=fault)
    runner.claim()
    try:
        with pytest.raises(AttemptError):
            execute(runner, "import time;time.sleep(20)")
        assert not runner.close(0)
        assert not runner.guard.closed and runner.guard.retained
        child = runner.children[0]
        assert child["process"].evidence().state == "exit_unknown"
        assert owner.journal.owned_attempt(runner.token)["child"]["exit"] is None
        with pytest.raises(OSError):
            runner.guard.revalidate().flv_inputs[0].open("ab")
        with pytest.raises(AttemptError):
            execute(runner)
    finally:
        for native, status, terminate in originals:
            monkeypatch.setattr(native, "status", status)
            monkeypatch.setattr(native, "terminate", terminate)
        runner._fault = lambda _: None
        assert runner.close(5)


@pytest.mark.parametrize("failure", ["observer", "cleanup"])
def test_exit_survives_stream_or_cleanup_failure(sealed, managed_process, monkeypatch, failure):
    owner, _, _ = sealed
    original_close = []
    def fault(point):
        if failure == "cleanup" and point == "native_after_resume":
            native = runner.children[-1]["process"].native
            original_close.append((native, native.close))
            def fail():
                raise OSError("exact native cleanup failed")
            monkeypatch.setattr(native, "close", fail)
    def observer(_name, _chunk):
        raise ValueError("diagnostic observer failed")
    runner = AttemptCoordinator(owner, process_factory=factory(managed_process), fault=fault)
    runner.claim()
    try:
        with pytest.raises(AttemptError):
            runner.run_child(Path(sys._base_executable), ["-c", "print('final bytes')"],
                cwd=owner.root, phase="probe", timeout=10, observer=observer if failure == "observer" else None)
        row = owner.journal.owned_attempt(runner.token)
        assert row["child"]["exit"]["state"] == "confirmed_exited"
        assert not row["child"]["diagnostics"]["complete"]
        if failure == "cleanup":
            assert row["child"]["cleanup"] == 0 and not runner.guard.closed
        with pytest.raises(AttemptError):
            execute(runner)
    finally:
        for native, close in original_close:
            monkeypatch.setattr(native, "close", close)
        runner._fault = lambda _: None
        assert runner.close()
