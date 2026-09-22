"""Bounded multi-recording ownership and durable-slot isolation tests."""

import json
from pathlib import Path
from threading import Event, Thread
from types import SimpleNamespace

import pytest

from tikrec.capture import CaptureError, CaptureResult
from tikrec.job_state import JobState, JobStateStore
from tikrec.recording import RecordingBusy, RecordingController
from tikrec.recording_manager import RecordingAmbiguous, RecordingManager
from tikrec.service_job import independent_job_stores, second_job_state_path


PAGE = "https://www.tiktok.com/@creator/live"


class CaptureHarness:
    """Hold independent workers until their own stop or explicit completion."""

    def __init__(self):
        self.entered = {}
        self.complete = {}
        self.stop_events = {}

    def capture(self, url, **kwargs):
        name = kwargs["output_path"].stem
        entered = self.entered.setdefault(name, Event())
        complete = self.complete.setdefault(name, Event())
        self.stop_events[name] = kwargs["stop_event"]
        kwargs["state"]("recording")
        entered.set()
        while not complete.wait(0.01):
            if kwargs["stop_event"].is_set():
                return CaptureResult((), kwargs["output_path"], True)
        return CaptureResult((), kwargs["output_path"])

    def wait(self, name):
        """Wait until one named worker owns its independent capture event."""
        assert self.entered.setdefault(name, Event()).wait(2)


def _manager(harness, *, stores=(None, None)):
    controllers = tuple(
        RecordingController(capture=harness.capture, store=store) for store in stores
    )
    return RecordingManager(controllers)


def test_two_jobs_run_with_distinct_sessions_then_reuse_only_freed_slot(tmp_path):
    harness = CaptureHarness()
    manager = _manager(harness)
    first = manager.start(PAGE, str(tmp_path / "first.mp4"))
    second = manager.start(PAGE, str(tmp_path / "second.mp4"))
    harness.wait("first")
    harness.wait("second")
    try:
        assert first["slot_id"] == "slot-1" and second["slot_id"] == "slot-2"
        assert first["session_id"] != second["session_id"]
        assert manager.health()["active_count"] == 2
        assert manager.health()["available_slots"] == 0
        with pytest.raises(RecordingBusy):
            manager.start(PAGE, str(tmp_path / "third.mp4"))
        with pytest.raises(RecordingAmbiguous):
            manager.status()
        with pytest.raises(RecordingAmbiguous):
            manager.stop()

        harness.complete["first"].set()
        manager.controllers[0]._worker.join(2)
        assert manager.controllers[1].status()["active"] is True
        assert manager.prior_session_id_for_start() == first["session_id"]
        third = manager.start(PAGE, str(tmp_path / "third.mp4"))
        harness.wait("third")
        assert third["slot_id"] == "slot-1"
        assert manager.controllers[1].status()["session_id"] == second["session_id"]

        stopped = manager.stop(second["session_id"])
        assert stopped["slot_id"] == "slot-2" and stopped["stop_requested"]
        assert harness.stop_events["second"].is_set()
        assert not harness.stop_events["third"].is_set()
    finally:
        manager.shutdown()


def test_cross_slot_output_and_parts_collision_is_rejected(tmp_path):
    harness = CaptureHarness()
    manager = _manager(harness)
    output = tmp_path / "same.mp4"
    manager.start(PAGE, str(output))
    harness.wait("same")
    try:
        with pytest.raises(ValueError, match="already owned"):
            manager.start(PAGE, str(output))
        alias = tmp_path / "unused-parent" / ".." / "same.mp4"
        with pytest.raises(ValueError, match="already owned"):
            manager.start(PAGE, str(alias))
    finally:
        manager.shutdown()


def test_one_failure_retains_its_progress_without_mutating_other_slot(tmp_path):
    steady_stop = Event()

    def capture(url, **kwargs):
        parts = kwargs["parts_directory"]
        parts.mkdir()
        part = parts / "part-0001.flv"
        part.write_bytes(b"one" if kwargs["output_path"].stem == "failed" else b"steady")
        kwargs["heartbeat"](part, part.stat().st_size)
        kwargs["state"]("recording")
        if kwargs["output_path"].stem == "failed":
            raise CaptureError("failed https://cdn.invalid/media?secret=value", (part,))
        steady_stop.set()
        assert kwargs["stop_event"].wait(2)
        return CaptureResult((part,), kwargs["output_path"], True)

    manager = RecordingManager((RecordingController(capture=capture),
                                RecordingController(capture=capture)))
    failed = manager.start(PAGE, str(tmp_path / "failed.mp4"))
    steady = manager.start(PAGE, str(tmp_path / "steady.mp4"))
    assert steady_stop.wait(2)
    manager.controllers[0]._worker.join(2)
    try:
        slots = manager.recordings()["slots"]
        assert slots[0]["session_id"] == failed["session_id"]
        assert slots[0]["state"] == "failed" and slots[0]["bytes_written"] == 3
        assert "secret" not in json.dumps(slots[0])
        assert slots[1]["session_id"] == steady["session_id"]
        assert slots[1]["state"] == "recording" and slots[1]["bytes_written"] == 6
        manager.stop(steady["session_id"])
        assert manager.controllers[0].status()["state"] == "failed"
    finally:
        manager.shutdown()


def test_global_shutdown_signals_and_joins_both_workers(tmp_path):
    harness = CaptureHarness()
    manager = _manager(harness)
    manager.start(PAGE, str(tmp_path / "one.mp4"))
    manager.start(PAGE, str(tmp_path / "two.mp4"))
    harness.wait("one")
    harness.wait("two")
    done = Event()
    worker = Thread(target=lambda: (manager.shutdown(), done.set()))
    worker.start()
    worker.join(2)
    assert done.is_set()
    assert harness.stop_events["one"].is_set()
    assert harness.stop_events["two"].is_set()
    assert manager.health()["shutting_down"] is True
    with pytest.raises(RecordingBusy):
        manager.start(PAGE, str(tmp_path / "three.mp4"))


def test_slots_persist_to_legacy_and_deterministic_second_paths(tmp_path):
    harness = CaptureHarness()
    first_path = tmp_path / "job.json"
    second_path = second_job_state_path(first_path)
    manager = _manager(
        harness, stores=(JobStateStore(first_path), JobStateStore(second_path))
    )
    first = manager.start(PAGE, str(tmp_path / "one.mp4"))
    second = manager.start(PAGE, str(tmp_path / "two.mp4"))
    harness.wait("one")
    harness.wait("two")
    try:
        assert first_path.is_file() and second_path == tmp_path / "job-2.json"
        assert second_path.is_file()
        assert JobStateStore(first_path).load().session_id == first["session_id"]
        assert JobStateStore(second_path).load().session_id == second["session_id"]
    finally:
        manager.shutdown()


def test_legacy_job_alone_leaves_second_slot_empty_and_available(tmp_path):
    first_path = tmp_path / "job.json"
    output = tmp_path / "old.mp4"
    JobStateStore(first_path).save(JobState(
        "00000000-0000-0000-0000-000000000001", PAGE, str(output),
        str(tmp_path / "old.parts"), 1.0, state="completed", ended_at=2.0,
        finalization_completed=True,
    ))
    second_path = second_job_state_path(first_path)
    manager = RecordingManager((
        RecordingController(store=JobStateStore(first_path)),
        RecordingController(store=JobStateStore(second_path)),
    ))
    try:
        assert manager.controllers[0].status()["state"] == "completed"
        assert manager.controllers[1].status()["state"] == "idle"
        assert manager.health()["available_slots"] == 2
        assert not second_path.exists()
    finally:
        manager.shutdown()


def test_corrupt_slot_preserves_evidence_while_healthy_slot_records(tmp_path):
    first_path = tmp_path / "job.json"
    first_path.write_text('{"signed_url":"https://secret.invalid/media"}', encoding="utf-8")
    original = first_path.read_bytes()
    harness = CaptureHarness()
    manager = _manager(
        harness,
        stores=(JobStateStore(first_path), JobStateStore(tmp_path / "job-2.json")),
    )
    try:
        health = manager.health()
        assert health["available_slots"] == 1
        assert health["slots"][0]["recovery_state"] == "failed"
        started = manager.start(PAGE, str(tmp_path / "healthy.mp4"))
        harness.wait("healthy")
        assert started["slot_id"] == "slot-2"
        assert first_path.read_bytes() == original
        assert "secret" not in json.dumps(manager.recordings())
    finally:
        manager.shutdown()


def test_colliding_interrupted_jobs_block_second_without_rewriting_it(tmp_path):
    output = tmp_path / "shared.mp4"
    paths = (tmp_path / "job.json", tmp_path / "job-2.json")
    for index, path in enumerate(paths, 1):
        JobStateStore(path).save(JobState(
            f"00000000-0000-0000-0000-{index:012d}", PAGE, str(output),
            str(tmp_path / "shared.parts"), 1.0, room_id=str(index),
        ))
    originals = tuple(path.read_bytes() for path in paths)
    first, second = independent_job_stores(
        JobStateStore(paths[0]), JobStateStore(paths[1])
    )
    assert first.load().session_id.endswith("1")
    with pytest.raises(Exception, match="preserve artifacts"):
        second.load()
    assert tuple(path.read_bytes() for path in paths) == originals


def test_status_failure_is_redacted_and_removes_that_slot_from_capacity():
    def failed_status():
        raise RuntimeError("https://cdn.invalid/media?token=secret")

    broken = SimpleNamespace(
        status=failed_status,
        health=lambda: {"available": True, "active": False},
        shutdown=lambda: None,
    )
    healthy = SlotLikeIdle()
    manager = RecordingManager((broken, healthy))
    aggregate = manager.recordings()
    assert aggregate["available_slots"] == 1
    assert aggregate["slots"][0]["error"] == "controller_state_unavailable"
    assert "secret" not in json.dumps(aggregate)
    assert manager.health()["available_slots"] == 1


class SlotLikeIdle:
    """Minimal healthy idle controller for redaction/capacity coverage."""

    def status(self):
        return {"state": "idle", "active": False}

    def health(self):
        return {"available": True, "active": False}

    def shutdown(self):
        pass


def test_two_startup_reconcilers_run_independently(tmp_path):
    entered = (Event(), Event())
    release = Event()

    class Reconciler:
        def __init__(self, index, job):
            self.index, self.job = index, job

        def reconcile(self, **kwargs):
            entered[self.index].set()
            assert release.wait(2)
            return SimpleNamespace(
                job=self.job, blocked=True, outcome="deferred",
                reason="identity_unavailable", error=None,
            )

    controllers = []
    for index, name in enumerate(("one", "two")):
        output = tmp_path / f"{name}.mp4"
        job = JobState(
            f"00000000-0000-0000-0000-{index + 1:012d}", PAGE, str(output),
            str(tmp_path / f"{name}.parts"), 1.0, room_id=str(index + 1),
        )
        store = JobStateStore(tmp_path / ("job.json" if index == 0 else "job-2.json"))
        store.save(job)
        controllers.append(
            RecordingController(store=store, reconciler=Reconciler(index, job))
        )
    manager = RecordingManager(tuple(controllers))
    assert entered[0].wait(2) and entered[1].wait(2)
    release.set()
    try:
        for controller in controllers:
            controller._worker.join(2)
        statuses = manager.recordings()["slots"]
        assert [item["session_id"] for item in statuses] == [
            "00000000-0000-0000-0000-000000000001",
            "00000000-0000-0000-0000-000000000002",
        ]
        assert all(item["recovery_state"] == "deferred" for item in statuses)
    finally:
        manager.shutdown()
