"""Bounded multi-recording ownership and durable-slot isolation tests."""

import json
from pathlib import Path
from threading import Barrier, Event, Thread
from types import SimpleNamespace

import pytest

from tikrec.capture import CaptureError, CaptureResult
from tikrec.job_state import JobState, JobStateStore
from tikrec.lifecycle_lock import LifecycleBusy, acquire_lifecycle
from tikrec.recording import RecordingBusy, RecordingController
from tikrec.recording_manager import (RecordingAmbiguous, RecordingDuplicate,
                                      RecordingManager)
from tikrec.service_job import independent_job_stores, second_job_state_path


PAGE = "https://www.tiktok.com/@creator/live"
MIXED_PAGE = "https://www.tiktok.com/@Alpha/live"
PAGE_BETA = "https://www.tiktok.com/@beta/live"
PAGE_GAMMA = "https://www.tiktok.com/@gamma/live"


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
    second = manager.start(PAGE_BETA, str(tmp_path / "second.mp4"))
    harness.wait("first")
    harness.wait("second")
    try:
        assert first["slot_id"] == "slot-1" and second["slot_id"] == "slot-2"
        assert first["session_id"] != second["session_id"]
        assert manager.health()["active_count"] == 2
        assert manager.health()["available_slots"] == 0
        with pytest.raises(RecordingBusy):
            manager.start(PAGE_GAMMA, str(tmp_path / "third.mp4"))
        with pytest.raises(RecordingAmbiguous):
            manager.status()
        with pytest.raises(RecordingAmbiguous):
            manager.stop()

        harness.complete["first"].set()
        manager.controllers[0]._worker.join(2)
        assert manager.controllers[1].status()["active"] is True
        assert manager.prior_session_id_for_start() == first["session_id"]
        third = manager.start(PAGE_GAMMA, str(tmp_path / "third.mp4"))
        harness.wait("third")
        assert third["slot_id"] == "slot-1"
        assert manager.controllers[1].status()["session_id"] == second["session_id"]

        stopped = manager.stop(second["session_id"])
        assert stopped["slot_id"] == "slot-2" and stopped["stop_requested"]
        assert harness.stop_events["second"].is_set()
        assert not harness.stop_events["third"].is_set()
    finally:
        manager.shutdown()


def test_two_service_slots_hold_compatible_writer_leases(tmp_path):
    harness = CaptureHarness()
    manager = _manager(harness)
    manager.start(PAGE, str(tmp_path / "first.mp4"))
    manager.start(PAGE_BETA, str(tmp_path / "second.mp4"))
    harness.wait("first")
    harness.wait("second")
    try:
        with pytest.raises(LifecycleBusy):
            acquire_lifecycle(tmp_path, "retention")
        assert manager.health()["active_count"] == 2
    finally:
        manager.shutdown()
    with acquire_lifecycle(tmp_path, "retention") as lease:
        lease.assert_held()


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


@pytest.mark.parametrize("alias", [False, True])
def test_pending_output_owner_survives_unreadable_status_with_durable_slots(
    tmp_path, monkeypatch, alias,
):
    entered = {PAGE: Event(), PAGE_BETA: Event()}
    def pending_capture(url, **kwargs):
        entered[url].set()
        assert kwargs["stop_event"].wait(3)
        return CaptureResult((), None, True)
    stores = (JobStateStore(tmp_path / "job.json"),
              JobStateStore(tmp_path / "job-2.json"))
    manager = RecordingManager(tuple(
        RecordingController(capture=pending_capture, store=store) for store in stores
    ))
    output = tmp_path / "shared.mp4"
    first = manager.start(PAGE, str(output))
    assert entered[PAGE].wait(2)
    assert not output.exists() and not (tmp_path / "shared.parts").exists()
    controller = manager.controllers[0]
    monkeypatch.setattr(controller, "status",
                        lambda: (_ for _ in ()).throw(OSError("rich status unavailable")))
    candidate = (tmp_path / "unused-parent" / ".." / "shared.mp4") if alias else output
    try:
        with pytest.raises(ValueError, match="already owned"):
            manager.start(PAGE_BETA, str(candidate))
        assert not entered[PAGE_BETA].is_set()
        assert stores[0].load().session_id == first["session_id"]
        assert stores[0].load().state == "resolving"
        assert stores[1].load() is None
        assert not controller._stop.is_set()
    finally:
        manager.shutdown()


def test_parts_path_collision_is_checked_without_rich_status(tmp_path, monkeypatch):
    entered = {PAGE: Event(), PAGE_BETA: Event()}
    def pending_capture(url, **kwargs):
        entered[url].set()
        assert kwargs["stop_event"].wait(3)
        return CaptureResult((), None, True)
    first_controller = RecordingController(capture=pending_capture)
    first_controller.start(PAGE, str(tmp_path / "original.mp4"))
    assert entered[PAGE].wait(2)
    manager = RecordingManager((first_controller,
                                RecordingController(capture=pending_capture)))
    # Isolate the parts guard: valid jobs derive this path from the output, so
    # their parts collision would ordinarily also be an output collision.
    narrow = first_controller.ownership()
    narrow["parts_directory"] = str(tmp_path / "shared.parts")
    monkeypatch.setattr(first_controller, "ownership", lambda: dict(narrow))
    monkeypatch.setattr(first_controller, "status",
                        lambda: (_ for _ in ()).throw(OSError("rich status unavailable")))
    try:
        with pytest.raises(ValueError, match="retained parts are already owned"):
            manager.start(PAGE_BETA, str(tmp_path / "shared.mp4"))
        assert not entered[PAGE_BETA].is_set()
    finally:
        manager.shutdown()


def test_uncached_missing_path_owner_blocks_then_recovers(tmp_path, monkeypatch):
    entered = {PAGE: Event(), PAGE_BETA: Event()}
    def pending_capture(url, **kwargs):
        entered[url].set()
        assert kwargs["stop_event"].wait(3)
        return CaptureResult((), None, True)
    first_controller = RecordingController(capture=pending_capture)
    first_controller.start(PAGE, str(tmp_path / "first.mp4"))
    assert entered[PAGE].wait(2)
    manager = RecordingManager((first_controller,
                                RecordingController(capture=pending_capture)))
    original_ownership = first_controller.ownership
    incomplete = original_ownership()
    incomplete["output_path"] = None
    monkeypatch.setattr(first_controller, "status",
                        lambda: (_ for _ in ()).throw(OSError("rich status unavailable")))
    monkeypatch.setattr(first_controller, "ownership", lambda: dict(incomplete))
    try:
        assert manager.health()["available_slots"] == 0
        with pytest.raises(RecordingBusy, match="ownership unavailable"):
            manager.start(PAGE_BETA, str(tmp_path / "second.mp4"))
        assert not entered[PAGE_BETA].is_set()
        monkeypatch.setattr(first_controller, "ownership", original_ownership)
        assert manager.health()["available_slots"] == 1
        second = manager.start(PAGE_BETA, str(tmp_path / "second.mp4"))
        assert second["slot_id"] == "slot-2"
        assert entered[PAGE_BETA].wait(2)
    finally:
        manager.shutdown()


def test_cached_paths_survive_partial_current_snapshot(tmp_path, monkeypatch):
    entered = Event()
    def pending_capture(url, **kwargs):
        entered.set()
        assert kwargs["stop_event"].wait(3)
        return CaptureResult((), None, True)
    manager = RecordingManager((RecordingController(capture=pending_capture),
                                RecordingController(capture=pending_capture)))
    first = manager.start(PAGE, str(tmp_path / "shared.mp4"))
    assert entered.wait(2)
    controller = manager.controllers[0]
    partial = controller.ownership()
    partial["output_path"] = None
    partial["parts_directory"] = "relative.parts"
    monkeypatch.setattr(controller, "status",
                        lambda: (_ for _ in ()).throw(OSError("rich status unavailable")))
    monkeypatch.setattr(controller, "ownership", lambda: dict(partial))
    try:
        assert manager.health()["available_slots"] == 1
        with pytest.raises(ValueError, match="already owned"):
            manager.start(PAGE_BETA, str(tmp_path / "shared.mp4"))
        assert controller._job["session_id"] == first["session_id"]
        assert not controller._stop.is_set()
    finally:
        manager.shutdown()


def test_settled_path_owner_releases_claim_for_later_slot_reuse(tmp_path):
    first_entered, later_entered, first_done = Event(), Event(), Event()
    def capture(url, **kwargs):
        if url == PAGE:
            first_entered.set()
            assert first_done.wait(3)
            return CaptureResult((), None)
        later_entered.set()
        assert kwargs["stop_event"].wait(3)
        return CaptureResult((), None, True)
    manager = RecordingManager((RecordingController(capture=capture),
                                RecordingController(capture=capture)))
    shared = str(tmp_path / "shared.mp4")
    first = manager.start(PAGE, shared)
    assert first_entered.wait(2)
    try:
        first_done.set()
        manager.controllers[0]._worker.join(2)
        assert manager.health()["available_slots"] == 2
        later = manager.start(PAGE_BETA, shared)
        assert later["slot_id"] == "slot-1"
        assert later["session_id"] != first["session_id"]
        assert later_entered.wait(2)
    finally:
        manager.shutdown()


def test_equivalent_manual_pages_cannot_own_two_slots(tmp_path):
    harness = CaptureHarness()
    manager = _manager(harness)
    first = manager.start(PAGE, str(tmp_path / "first.mp4"))
    harness.wait("first")
    try:
        with pytest.raises(RecordingDuplicate):
            manager.start("http://tiktok.com/@creator/live/?share=1#fragment",
                          str(tmp_path / "second.mp4"))
        assert manager.health()["active_count"] == 1
        assert manager.status()["session_id"] == first["session_id"]
        assert not harness.stop_events["first"].is_set()
    finally:
        manager.shutdown()


@pytest.mark.parametrize("candidate", [
    "https://www.tiktok.com/@alpha/live",
    "http://tiktok.com/@aLpHa/live/?share=1#fragment",
])
def test_case_equivalent_manual_pages_cannot_own_two_slots(tmp_path, candidate):
    harness = CaptureHarness()
    manager = _manager(harness)
    first = manager.start(MIXED_PAGE, str(tmp_path / "first.mp4"))
    harness.wait("first")
    try:
        with pytest.raises(RecordingDuplicate):
            manager.start(candidate, str(tmp_path / "second.mp4"))
        assert manager.health()["active_count"] == 1
        assert manager.status()["session_id"] == first["session_id"]
        assert manager.status()["source_url"] == MIXED_PAGE
        assert not harness.stop_events["first"].is_set()
    finally:
        manager.shutdown()


def test_expected_room_reservation_is_scoped_to_current_session(tmp_path):
    harness = CaptureHarness()
    first_store = JobStateStore(tmp_path / "job.json")
    manager = _manager(harness, stores=(first_store, None))
    first = manager.start("https://www.tiktok.com/@alpha/live",
                          str(tmp_path / "first.mp4"), expected_room_id="123")
    harness.wait("first")
    try:
        assert first_store.load().room_id is None
        with pytest.raises(RecordingDuplicate):
            manager.start("https://www.tiktok.com/@beta/live",
                          str(tmp_path / "blocked.mp4"), expected_room_id="123")
        harness.complete["first"].set()
        manager.controllers[0]._worker.join(2)
        assert manager.controllers[0].status()["session_id"] == first["session_id"]
        second = manager.start("https://www.tiktok.com/@beta/live",
                               str(tmp_path / "second.mp4"), expected_room_id="456")
        harness.wait("second")
        third = manager.start("https://www.tiktok.com/@gamma/live",
                              str(tmp_path / "third.mp4"), expected_room_id="123")
        harness.wait("third")
        assert second["slot_id"] == "slot-1" and third["slot_id"] == "slot-2"
        with pytest.raises(RecordingDuplicate):
            manager.start("https://www.tiktok.com/@delta/live",
                          str(tmp_path / "again.mp4"), expected_room_id="456")
    finally:
        manager.shutdown()


def test_failed_expected_room_owner_releases_reservation(tmp_path):
    entered = Event()
    def capture(url, **kwargs):
        entered.set()
        raise CaptureError("offline", ())
    manager = RecordingManager((RecordingController(capture=capture),
                                RecordingController(capture=capture)))
    try:
        manager.start("https://www.tiktok.com/@alpha/live",
                      str(tmp_path / "first.mp4"), expected_room_id="123")
        assert entered.wait(2)
        manager.controllers[0]._worker.join(2)
        later = manager.start("https://www.tiktok.com/@beta/live",
                              str(tmp_path / "later.mp4"), expected_room_id="123")
        assert later["slot_id"] == "slot-1"
    finally:
        manager.shutdown()


def test_unavailable_status_does_not_erase_unproven_room_owner(tmp_path, monkeypatch):
    harness = CaptureHarness()
    manager = _manager(harness)
    manager.start("https://www.tiktok.com/@alpha/live",
                  str(tmp_path / "first.mp4"), expected_room_id="123")
    harness.wait("first")
    controller = manager.controllers[0]
    original_status = controller.status
    failures = 0
    def unavailable_twice():
        nonlocal failures
        failures += 1
        if failures <= 2:
            raise OSError("temporary status failure")
        return original_status()
    monkeypatch.setattr(controller, "status", unavailable_twice)
    try:
        assert manager.health()["available_slots"] == 1
        with pytest.raises(RecordingDuplicate):
            manager.start("https://www.tiktok.com/@beta/live",
                          str(tmp_path / "second.mp4"), expected_room_id="123")
        assert manager.health()["active_count"] == 1
    finally:
        manager.shutdown()


def test_unavailable_status_does_not_erase_manual_page_owner(tmp_path, monkeypatch):
    harness = CaptureHarness()
    manager = _manager(harness)
    first = manager.start(PAGE, str(tmp_path / "first.mp4"))
    harness.wait("first")
    controller = manager.controllers[0]
    original_status = controller.status
    failures = 0
    def unavailable_twice():
        nonlocal failures
        failures += 1
        if failures <= 2:
            raise OSError("temporary status failure")
        return original_status()
    monkeypatch.setattr(controller, "status", unavailable_twice)
    try:
        assert manager.health()["available_slots"] == 1
        with pytest.raises(RecordingDuplicate):
            manager.start(PAGE, str(tmp_path / "second.mp4"))
        assert manager.status()["session_id"] == first["session_id"]
    finally:
        manager.shutdown()


def test_unavailable_status_preserves_mixed_case_page_owner(tmp_path, monkeypatch):
    harness = CaptureHarness()
    manager = _manager(harness)
    first = manager.start(MIXED_PAGE, str(tmp_path / "first.mp4"))
    harness.wait("first")
    controller = manager.controllers[0]
    original_status = controller.status
    failures = 0
    def unavailable_twice():
        nonlocal failures
        failures += 1
        if failures <= 2:
            raise OSError("temporary status failure")
        return original_status()
    monkeypatch.setattr(controller, "status", unavailable_twice)
    try:
        assert manager.health()["available_slots"] == 1
        with pytest.raises(RecordingDuplicate):
            manager.start("https://www.tiktok.com/@alpha/live",
                          str(tmp_path / "second.mp4"))
        assert manager.status()["session_id"] == first["session_id"]
    finally:
        manager.shutdown()


def test_concurrent_same_room_claims_have_one_winner(tmp_path):
    harness = CaptureHarness()
    manager = _manager(harness)
    gate = Barrier(3)
    results = []
    def start(name):
        gate.wait()
        try:
            results.append(manager.start(f"https://www.tiktok.com/@{name}/live",
                                         str(tmp_path / f"{name}.mp4"),
                                         expected_room_id="123"))
        except RecordingDuplicate:
            results.append("duplicate")
    threads = [Thread(target=start, args=(name,)) for name in ("alpha", "beta")]
    try:
        for worker in threads:
            worker.start()
        gate.wait()
        for worker in threads:
            worker.join(2)
        assert len(results) == 2
        assert sum(isinstance(item, dict) for item in results) == 1
        assert results.count("duplicate") == 1
        assert manager.health()["active_count"] == 1
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
    steady = manager.start(PAGE_BETA, str(tmp_path / "steady.mp4"))
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
    manager.start(PAGE_BETA, str(tmp_path / "two.mp4"))
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
    second = manager.start(PAGE_BETA, str(tmp_path / "two.mp4"))
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


def test_loaded_mixed_case_durable_job_owns_equivalent_page(tmp_path):
    path = tmp_path / "job.json"
    output = tmp_path / "old.mp4"
    job = JobState(
        "00000000-0000-0000-0000-000000000001", MIXED_PAGE, str(output),
        str(tmp_path / "old.parts"), 1.0, room_id="123",
    )
    store = JobStateStore(path)
    store.save(job)
    original = path.read_bytes()
    reconciler = SimpleNamespace(reconcile=lambda **_: SimpleNamespace(
        job=job, blocked=True, outcome="deferred", reason="identity_unavailable",
        error=None,
    ))
    controller = RecordingController(store=store, reconciler=reconciler)
    controller._worker.join(2)
    harness = CaptureHarness()
    manager = RecordingManager((controller, RecordingController(capture=harness.capture)))
    try:
        assert manager.controllers[0].status()["source_url"] == MIXED_PAGE
        assert manager.health()["available_slots"] == 1
        with pytest.raises(RecordingDuplicate):
            manager.start("https://www.tiktok.com/@alpha/live",
                          str(tmp_path / "second.mp4"))
        assert path.read_bytes() == original
        assert store.load().source_url == MIXED_PAGE
    finally:
        manager.shutdown()


def _resumed_manager(tmp_path):
    """Resume a durable room into a real active controller without network use."""
    output = tmp_path / "restored.mp4"
    job = JobState(
        "00000000-0000-0000-0000-000000000001", MIXED_PAGE, str(output),
        str(tmp_path / "restored.parts"), 1.0, state="recording", room_id="123",
    )
    store = JobStateStore(tmp_path / "job.json")
    store.save(job)
    entered = Event()
    class Reconciler:
        def reconcile(self, **kwargs):
            return SimpleNamespace(job=job, blocked=False, outcome="resume",
                                   reason=None, error=None)
        def resume(self, recovery, **kwargs):
            entered.set()
            assert kwargs["stop_event"].wait(3)
            return CaptureResult((), None, True)
    restored = RecordingController(store=store, reconciler=Reconciler())
    assert entered.wait(2)
    harness = CaptureHarness()
    manager = RecordingManager((restored, RecordingController(capture=harness.capture)))
    return manager, restored, store, harness


@pytest.mark.parametrize("candidate,room", [
    ("https://www.tiktok.com/@alpha/live", None),
    ("https://www.tiktok.com/@beta/live", "123"),
])
def test_restored_owner_survives_later_rich_status_failure(
    tmp_path, monkeypatch, candidate, room,
):
    manager, restored, store, harness = _resumed_manager(tmp_path)
    session = restored.status()["session_id"]
    assert manager.health()["active_count"] == 1
    monkeypatch.setattr(restored, "status", lambda: (_ for _ in ()).throw(OSError("status")))
    try:
        with pytest.raises(RecordingDuplicate):
            manager.start(candidate, str(tmp_path / "second.mp4"),
                          **({} if room is None else {"expected_room_id": room}))
        assert manager.health()["active_count"] == 1
        assert restored._job["session_id"] == session
        assert restored.health()["active"] is True
        assert not restored._stop.is_set()
        assert store.load().source_url == MIXED_PAGE
        assert "second" not in harness.entered
    finally:
        manager.shutdown()


def test_restored_owner_is_protected_on_first_unreadable_status(tmp_path, monkeypatch):
    manager, restored, _, harness = _resumed_manager(tmp_path)
    monkeypatch.setattr(restored, "status", lambda: (_ for _ in ()).throw(OSError("status")))
    try:
        with pytest.raises(RecordingDuplicate):
            manager.start("https://www.tiktok.com/@alpha/live",
                          str(tmp_path / "second.mp4"))
        assert "second" not in harness.entered
    finally:
        manager.shutdown()


def test_restored_path_owner_hydrates_on_first_unreadable_status(tmp_path, monkeypatch):
    manager, restored, store, harness = _resumed_manager(tmp_path)
    prior = store.path.read_bytes()
    monkeypatch.setattr(restored, "status",
                        lambda: (_ for _ in ()).throw(OSError("rich status unavailable")))
    try:
        with pytest.raises(ValueError, match="already owned"):
            manager.start(PAGE_BETA, str(tmp_path / "restored.mp4"))
        assert "restored" not in harness.entered
        assert store.path.read_bytes() == prior
        assert restored.health()["active"] is True
        assert not restored._stop.is_set()
    finally:
        manager.shutdown()


def test_unknown_restored_owner_fails_allocation_closed(tmp_path, monkeypatch):
    manager, restored, _, harness = _resumed_manager(tmp_path)
    monkeypatch.setattr(restored, "status", lambda: (_ for _ in ()).throw(OSError("status")))
    monkeypatch.setattr(restored, "ownership", lambda: (_ for _ in ()).throw(OSError("owner")),
                        raising=False)
    try:
        assert manager.health()["available_slots"] == 0
        with pytest.raises(RecordingBusy) as error:
            manager.start("https://www.tiktok.com/@beta/live",
                          str(tmp_path / "second.mp4"), expected_room_id="456")
        assert type(error.value) is RecordingBusy
        assert "second" not in harness.entered
    finally:
        manager.shutdown()


def test_first_unreadable_active_owner_cannot_allocate_second_slot(tmp_path, monkeypatch):
    harness = CaptureHarness()
    first_controller = RecordingController(capture=harness.capture)
    first = first_controller.start(MIXED_PAGE, str(tmp_path / "first.mp4"))
    harness.wait("first")
    manager = RecordingManager((first_controller,
                                RecordingController(capture=harness.capture)))
    original_reads = (first_controller.status, first_controller.health,
                      first_controller.ownership)
    def unreadable():
        raise OSError("controller read failed")
    for method in ("status", "health", "ownership"):
        monkeypatch.setattr(first_controller, method, unreadable)
    try:
        assert manager.health()["available_slots"] == 0
        assert manager.recordings()["available_slots"] == 0
        with pytest.raises(RecordingBusy) as error:
            manager.start("https://www.tiktok.com/@alpha/live",
                          str(tmp_path / "duplicate.mp4"))
        assert type(error.value) is RecordingBusy
        assert "duplicate" not in harness.entered
        assert first_controller._job["session_id"] == first["session_id"]
        assert not harness.stop_events["first"].is_set()

        for method, original in zip(("status", "health", "ownership"), original_reads):
            monkeypatch.setattr(first_controller, method, original)
        assert manager.health()["available_slots"] == 1
        with pytest.raises(RecordingDuplicate):
            manager.start("https://www.tiktok.com/@alpha/live",
                          str(tmp_path / "still-duplicate.mp4"))
        harness.complete["first"].set()
        first_controller._worker.join(2)
        assert manager.health()["available_slots"] == 2
        later = manager.start(PAGE_BETA, str(tmp_path / "later.mp4"))
        harness.wait("later")
        assert later["slot_id"] == "slot-1"
    finally:
        manager.shutdown()


def test_ambiguous_blocked_owner_unreadable_on_first_observation(
    tmp_path, monkeypatch,
):
    job = JobState(
        "00000000-0000-0000-0000-000000000001", MIXED_PAGE,
        str(tmp_path / "restored.mp4"), str(tmp_path / "restored.parts"),
        1.0, state="recording", room_id="123",
    )
    store = JobStateStore(tmp_path / "job.json")
    store.save(job)
    original_job = store.path.read_bytes()
    class Reconciler:
        def reconcile(self, **kwargs):
            return SimpleNamespace(job=job, blocked=True, outcome="failed",
                                   reason="ambiguous_state", error="startup recovery failed")
    blocked = RecordingController(store=store, reconciler=Reconciler())
    blocked._worker.join(2)
    harness = CaptureHarness()
    manager = RecordingManager((blocked, RecordingController(capture=harness.capture)))
    assert blocked.health()["recovery_reason"] == "ambiguous_state"
    original_status, original_ownership = blocked.status, blocked.ownership
    def unreadable():
        raise OSError("controller read failed")
    monkeypatch.setattr(blocked, "status", unreadable)
    monkeypatch.setattr(blocked, "ownership", unreadable)
    try:
        assert manager.health()["available_slots"] == 0
        for candidate, options in (
            ("https://www.tiktok.com/@alpha/live", {}),
            (PAGE_BETA, {"expected_room_id": "123"}),
        ):
            with pytest.raises(RecordingBusy):
                manager.start(candidate, str(tmp_path / "duplicate.mp4"), **options)
        assert "duplicate" not in harness.entered
        assert store.path.read_bytes() == original_job

        monkeypatch.setattr(blocked, "status", original_status)
        monkeypatch.setattr(blocked, "ownership", original_ownership)
        assert manager.health()["available_slots"] == 1
        with pytest.raises(RecordingDuplicate):
            manager.start(PAGE_BETA, str(tmp_path / "same-room.mp4"),
                          expected_room_id="123")
        distinct = manager.start(PAGE_BETA, str(tmp_path / "distinct.mp4"),
                                 expected_room_id="456")
        harness.wait("distinct")
        assert distinct["slot_id"] == "slot-2"
    finally:
        manager.shutdown()


def test_proven_empty_corrupt_slot_still_allows_healthy_slot(
    tmp_path, monkeypatch,
):
    corrupt = tmp_path / "job.json"
    corrupt.write_text('{"invalid":"durable state"}', encoding="utf-8")
    harness = CaptureHarness()
    manager = _manager(harness, stores=(JobStateStore(corrupt), None))
    first = manager.controllers[0]
    assert first.health()["recovery_reason"] == "ambiguous_state"
    assert first.ownership()["current"] is False
    monkeypatch.setattr(first, "status", lambda: (_ for _ in ()).throw(OSError("status")))
    try:
        assert manager.health()["available_slots"] == 1
        started = manager.start(PAGE_BETA, str(tmp_path / "healthy.mp4"))
        harness.wait("healthy")
        assert started["slot_id"] == "slot-2"
    finally:
        manager.shutdown()


def test_page_only_cache_fails_closed_when_both_reads_fail(tmp_path, monkeypatch):
    harness = CaptureHarness()
    manager = _manager(harness)
    first = manager.start(MIXED_PAGE, str(tmp_path / "first.mp4"))
    harness.wait("first")
    controller = manager.controllers[0]
    monkeypatch.setattr(controller, "status", lambda: (_ for _ in ()).throw(OSError("status")))
    monkeypatch.setattr(controller, "ownership", lambda: (_ for _ in ()).throw(OSError("owner")))
    try:
        assert manager.health()["available_slots"] == 0
        with pytest.raises(RecordingBusy) as error:
            manager.start(PAGE_BETA, str(tmp_path / "second.mp4"), expected_room_id="456")
        assert type(error.value) is RecordingBusy
        assert controller._job["session_id"] == first["session_id"]
        assert not harness.stop_events["first"].is_set()
        assert "second" not in harness.entered
    finally:
        manager.shutdown()


def test_manual_later_proven_room_survives_status_failure(tmp_path, monkeypatch):
    proven = Event()
    def capture(url, **kwargs):
        kwargs["room_identity"]("123")
        proven.set()
        assert kwargs["stop_event"].wait(3)
        return CaptureResult((), None, True)
    manager = RecordingManager((RecordingController(capture=capture),
                                RecordingController(capture=capture)))
    first = manager.start(MIXED_PAGE, str(tmp_path / "first.mp4"))
    assert proven.wait(2)
    controller = manager.controllers[0]
    assert controller.status()["room_id"] == "123"
    assert manager.health()["active_count"] == 1
    monkeypatch.setattr(controller, "status", lambda: (_ for _ in ()).throw(OSError("status")))
    try:
        with pytest.raises(RecordingDuplicate):
            manager.start(PAGE_BETA, str(tmp_path / "second.mp4"), expected_room_id="123")
        assert manager.health()["active_count"] == 1
        assert controller._job["session_id"] == first["session_id"]
        assert controller._job["room_id"] == "123"
    finally:
        manager.shutdown()


def test_known_owner_survives_partial_and_failed_snapshot_reads(tmp_path, monkeypatch):
    harness = CaptureHarness()
    manager = _manager(harness)
    first = manager.start(MIXED_PAGE, str(tmp_path / "first.mp4"))
    harness.wait("first")
    controller = manager.controllers[0]
    controller._identity("123")
    assert manager.health()["active_count"] == 1
    original_status = controller.status
    original_ownership = controller.ownership
    monkeypatch.setattr(controller, "status", lambda: (_ for _ in ()).throw(OSError("status")))
    try:
        monkeypatch.setattr(controller, "ownership", lambda: {
            "current": True, "session_id": first["session_id"],
            "source_url": MIXED_PAGE, "room_id": None,
        })
        with pytest.raises(RecordingDuplicate):
            manager.start(PAGE_BETA, str(tmp_path / "partial.mp4"), expected_room_id="123")
        monkeypatch.setattr(controller, "ownership",
                            lambda: (_ for _ in ()).throw(OSError("owner")))
        with pytest.raises(RecordingDuplicate):
            manager.start(PAGE_BETA, str(tmp_path / "unreadable.mp4"), expected_room_id="123")
        monkeypatch.setattr(controller, "status", original_status)
        monkeypatch.setattr(controller, "ownership", original_ownership)
        assert manager.status()["session_id"] == first["session_id"]
        assert manager.status()["room_id"] == "123"
        assert "partial" not in harness.entered and "unreadable" not in harness.entered
    finally:
        manager.shutdown()


def test_learned_room_claim_releases_after_settlement_and_slot_reuse(tmp_path):
    harness = CaptureHarness()
    manager = _manager(harness)
    first = manager.start(MIXED_PAGE, str(tmp_path / "first.mp4"))
    harness.wait("first")
    try:
        manager.controllers[0]._identity("123")
        assert manager.health()["active_count"] == 1
        harness.complete["first"].set()
        manager.controllers[0]._worker.join(2)
        assert manager.controllers[0].status()["state"] == "completed"
        second = manager.start(PAGE_BETA, str(tmp_path / "second.mp4"),
                               expected_room_id="456")
        harness.wait("second")
        later = manager.start("https://www.tiktok.com/@alpha/live",
                              str(tmp_path / "later.mp4"), expected_room_id="123")
        harness.wait("later")
        assert first["session_id"] != second["session_id"]
        assert second["slot_id"] == "slot-1" and later["slot_id"] == "slot-2"
        assert manager.health()["active_count"] == 2
    finally:
        manager.shutdown()
