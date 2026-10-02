"""Offline cycle-boundary reload, failure and shutdown regressions."""

from threading import Event, Thread

import pytest

from tikrec.configuration import Configuration, ConfigurationStore
from tikrec.monitoring import CreatorMonitor
from tikrec.tiktok_identity import LiveResolution


def _monitor(tmp_path, creators=("first",), **kwargs):
    store = ConfigurationStore(tmp_path / "config.json")
    store.save(Configuration(monitored_creators=creators))
    loader = lambda: store.load(missing_ok=False).monitored_creators
    monitor = CreatorMonitor(creators, creator_loader=loader, **kwargs)
    return monitor, store


def _names(snapshot):
    return [item["creator"] for item in snapshot["creators"]]


def test_add_remove_and_reorder_are_complete_cycle_snapshots(tmp_path):
    callbacks, calls = [], []
    monitor, store = _monitor(
        tmp_path, resolver=lambda page: calls.append(page) or
        LiveResolution("1", "https://cdn.test/live.flv"),
        cycle_completed=callbacks.append,
    )
    monitor._poll_cycle()
    store.save(Configuration(monitored_creators=("second", "first")))
    monitor._poll_cycle()
    store.save(Configuration(monitored_creators=("second",)))
    monitor._poll_cycle()
    store.save(Configuration())
    monitor._poll_cycle()
    assert [_names(s) for s in callbacks] == [
        ["first"], ["second", "first"], ["second"], [],
    ]
    assert len(calls) == 4
    assert all(not s["cycle_in_progress"] for s in callbacks)


@pytest.mark.parametrize("invalid", [
    '{', '{"schema_version":1,"monitored_creators":["Bad"]}',
    '{"schema_version":1,"monitored_creators":["first","first"]}',
    '{"schema_version":1,"monitored_creators":null}',
    '{"schema_version":1,"monitored_creators":[],"monitored_creators":["second"]}',
    '{"schema_version":2,"monitored_creators":["second"]}',
    '{"schema_version":1,"monitored_creators":["second"],"unknown":"secret"}',
    '{"schema_version":1,"monitored_creators":["second"],"debug_tracebacks":null}',
    '\ufeff{"schema_version":1,"monitored_creators":["second"]}',
])
def test_invalid_replacement_keeps_last_good_and_later_recovers(tmp_path, invalid):
    callbacks = []
    monitor, store = _monitor(
        tmp_path, resolver=lambda _: LiveResolution("1", "https://cdn.test/live.flv"),
        cycle_completed=callbacks.append,
    )
    monitor._poll_cycle()
    store.path.write_text(invalid, encoding="utf-8")
    monitor._poll_cycle()
    assert _names(callbacks[-1]) == ["first"]
    assert monitor.snapshot()["configuration"] == {
        "state": "unavailable", "reason": "configuration_unavailable",
    }
    assert "secret" not in str(monitor.snapshot())
    store.save(Configuration(monitored_creators=("second",)))
    monitor._poll_cycle()
    assert _names(callbacks[-1]) == ["second"]
    assert monitor.snapshot()["configuration"] == {"state": "ok", "reason": None}


def test_missing_and_unreadable_replacement_keep_last_good(tmp_path, monkeypatch):
    monitor, store = _monitor(tmp_path)
    store.path.unlink()
    monitor._poll_cycle()
    assert _names(monitor.snapshot()) == ["first"]
    assert monitor.snapshot()["configuration"]["state"] == "unavailable"
    store.save(Configuration(monitored_creators=("second",)))
    with monkeypatch.context() as patch:
        patch.setattr(store, "load", lambda **_: (_ for _ in ()).throw(
            PermissionError("secret path and credentials")))
        monitor._poll_cycle()
        assert _names(monitor.snapshot()) == ["first"]
        assert "secret" not in str(monitor.snapshot())
    monitor._poll_cycle()
    assert _names(monitor.snapshot()) == ["second"]


def test_empty_initial_list_worker_can_adopt_later_publication(tmp_path):
    first, second, advance = Event(), Event(), Event()
    waits = []
    callbacks = []

    def waiter(_):
        waits.append(True)
        if len(waits) == 1:
            first.set()
            assert advance.wait(3)
            return False
        second.set()
        return True

    monitor, store = _monitor(
        tmp_path, (), waiter=waiter, cycle_completed=callbacks.append,
        resolver=lambda _: LiveResolution("1", "https://cdn.test/live.flv"),
    )
    try:
        monitor.start()
        assert first.wait(3)
        store.save(Configuration(monitored_creators=("added",)))
        advance.set()
        assert second.wait(3)
        monitor.join()
        assert [_names(s) for s in callbacks] == [[], ["added"]]
    finally:
        advance.set()
        monitor.shutdown()


def test_change_during_observation_waits_for_next_serial_cycle(tmp_path):
    entered, release, second_waiting = Event(), Event(), Event()
    calls, callbacks = [], []

    def resolver(page):
        creator = page.split("@")[1].split("/")[0]
        calls.append(creator)
        if len(calls) == 1:
            entered.set()
            assert release.wait(3)
        return LiveResolution("1", "https://cdn.test/live.flv")

    monitor, store = _monitor(
        tmp_path, ("first", "second"), resolver=resolver,
        cycle_completed=callbacks.append,
    )
    worker = Thread(target=monitor._poll_cycle)
    def next_cycle():
        second_waiting.set()
        monitor._poll_cycle()
    other = Thread(target=next_cycle)
    try:
        worker.start()
        assert entered.wait(3)
        store.save(Configuration(monitored_creators=("third",)))
        other.start()
        assert second_waiting.wait(3)
        assert _names(monitor.snapshot()) == ["first", "second"]
        assert calls == ["first"]
        release.set()
        worker.join(3)
        other.join(3)
        assert not worker.is_alive() and not other.is_alive()
        assert calls == ["first", "second", "third"]
        assert [_names(s) for s in callbacks] == [["first", "second"], ["third"]]
        assert [s["cycle_count"] for s in callbacks] == [1, 2]
    finally:
        release.set()
        worker.join(3)
        if other.ident is not None:
            other.join(3)


def test_shutdown_during_config_read_prevents_adoption_and_callback(tmp_path):
    entered, release = Event(), Event()
    callbacks = []

    def loader():
        entered.set()
        assert release.wait(3)
        return ("second",)

    monitor = CreatorMonitor(("first",), creator_loader=loader,
                             cycle_completed=callbacks.append)
    worker = Thread(target=monitor._poll_cycle)
    try:
        worker.start()
        assert entered.wait(3)
        monitor.stop()
        release.set()
        worker.join(3)
        assert not worker.is_alive()
        assert _names(monitor.snapshot()) == ["first"]
        assert callbacks == []
        assert monitor.snapshot()["cycle_count"] == 0
    finally:
        release.set()
        worker.join(3)


def test_stop_in_final_resolver_never_publishes_completed_cycle():
    callbacks = []
    def resolver(_):
        monitor.stop()
        return LiveResolution("1", "https://cdn.test/live.flv")
    monitor = CreatorMonitor(("first",), creator_loader=lambda: ("first",),
                             resolver=resolver, cycle_completed=callbacks.append)
    monitor._poll_cycle()
    assert callbacks == []
    assert monitor.snapshot()["cycle_count"] == 0


def test_next_reload_waits_for_current_automatic_start_arbitration(tmp_path):
    entered, release, queued = Event(), Event(), Event()
    callbacks, reads = [], []
    store = ConfigurationStore(tmp_path / "config.json")
    store.save(Configuration(monitored_creators=("first",)))
    def loader():
        reads.append(True)
        return store.load(missing_ok=False).monitored_creators
    def callback(snapshot):
        callbacks.append(snapshot)
        if len(callbacks) == 1:
            entered.set()
            assert release.wait(3)
            assert _names(monitor.snapshot()) == ["first"]
    monitor = CreatorMonitor(
        ("first",), creator_loader=loader, cycle_completed=callback,
        resolver=lambda _: LiveResolution("1", "https://cdn.test/live.flv"),
    )
    first = Thread(target=monitor._poll_cycle)
    def next_cycle():
        queued.set()
        monitor._poll_cycle()
    second = Thread(target=next_cycle)
    try:
        first.start()
        assert entered.wait(3)
        store.save(Configuration(monitored_creators=("second",)))
        second.start()
        assert queued.wait(3)
        assert len(reads) == 1
        assert _names(monitor.snapshot()) == ["first"]
        release.set()
        first.join(3)
        second.join(3)
        assert not first.is_alive() and not second.is_alive()
        assert [_names(s) for s in callbacks] == [["first"], ["second"]]
    finally:
        release.set()
        first.join(3)
        if second.ident is not None:
            second.join(3)
