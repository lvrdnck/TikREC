"""Configuration publication shares only retention's final removal boundary."""

import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from io import StringIO

import pytest

from tikrec.configuration import Configuration, ConfigurationStore
from tikrec.policy_lock import policy_lock


def test_config_promotion_waits_while_readers_see_committed_policy(tmp_path):
    store = ConfigurationStore(tmp_path / "config.json")
    original = Configuration(retention_max_age_days=1)
    protected = replace(original, retention_protected_creators=("alpha",))
    store.save(original)
    started = threading.Event()

    def save():
        started.set()
        store.save(protected)

    with ThreadPoolExecutor() as pool:
        with policy_lock(store.path):
            future = pool.submit(save)
            assert started.wait(2)
            assert store.load() == original
            assert not future.done()
        future.result(timeout=3)
    assert store.load() == protected


def test_unrelated_read_and_write_work_outside_short_mutation_guard(tmp_path):
    store = ConfigurationStore(tmp_path / "config.json")
    store.save(Configuration(retention_max_age_days=1))
    # Slow planning/quarantine proof has no policy lease, so writes remain available.
    store.update(lambda current: replace(current, debug_tracebacks=True))
    assert store.load().effective_debug_tracebacks
    with policy_lock(store.path):
        assert store.load().retention_max_age_days == 1


def test_atomic_update_preserves_a_newer_protection_list(tmp_path):
    store = ConfigurationStore(tmp_path / "config.json")
    store.save(Configuration(retention_max_age_days=1))
    stale = store.load()
    store.update(lambda current: replace(current, retention_protected_creators=("alpha",)))
    store.update(lambda current: replace(current, debug_tracebacks=True))
    assert store.load().retention_protected_creators == ("alpha",)
    assert stale.retention_protected_creators == ()


@pytest.mark.parametrize("command", [
    ["config", "set", "debug-tracebacks", "true"],
    ["monitor", "add", "beta"],
    ["retention", "protect", "beta"],
])
def test_public_command_does_not_overwrite_policy_from_an_earlier_load(
        tmp_path, monkeypatch, command):
    from tikrec.cli import main

    store = ConfigurationStore(tmp_path / "config.json")
    store.save(Configuration(retention_max_age_days=1))
    load, changed = ConfigurationStore.load, False

    def race(self):
        nonlocal changed
        current = load(self)
        if not changed:
            changed = True
            self.save(replace(current, retention_protected_creators=("alpha",)))
        return current

    monkeypatch.setattr(ConfigurationStore, "load", race)
    assert main(["--config", str(store.path), *command], stdout=StringIO()) == 0
    assert "alpha" in store.load().retention_protected_creators
