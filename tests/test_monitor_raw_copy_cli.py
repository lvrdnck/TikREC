"""Offline persistence, normalization and strict automatic raw-copy configuration."""

import json
from io import StringIO

import pytest

from tikrec.cli import main
from tikrec.configuration import Configuration, ConfigurationError, ConfigurationStore
from tikrec.service_configuration import load_service_configuration


def command(path, *args, stdout=None, stderr=None):
    return main(["--config", str(path), "monitor", *args],
                stdout=stdout or StringIO(), stderr=stderr or StringIO(),
                resolver=lambda _: pytest.fail("configuration must remain offline"))


def test_missing_list_and_legacy_configuration_default_off(tmp_path):
    path = tmp_path / "config.json"
    shown = StringIO()
    assert command(path, "raw-copy", "list", stdout=shown) == 0
    assert shown.getvalue() == "No automatic raw-copy creators.\n"
    assert not path.exists()
    assert ConfigurationStore(path).load().automatic_raw_copy_creators == ()
    path.write_text('{"schema_version":1,"monitored_creators":["alpha"]}')
    for full in (True, False):
        assert load_service_configuration(path, validate_all=full).automatic_raw_copy_creators == ()


def test_normalized_preferences_are_independent_and_survive_monitor_removal(tmp_path):
    path = tmp_path / "config.json"
    store = ConfigurationStore(path)
    store.save(Configuration(monitored_creators=("alpha", "beta"),
                             retention_protected_creators=("protected",),
                             retention_max_age_days=30, minimum_free_space_gib=15))
    values = ("@ALPHA", "https://www.tiktok.com/@Gamma/live?lang=en", " Delta ")
    for value in values:
        assert command(path, "raw-copy", "enable", value) == 0
    assert store.load().automatic_raw_copy_creators == ("alpha", "gamma", "delta")
    assert command(path, "remove", "alpha") == 0
    assert store.load().automatic_raw_copy_creators == ("alpha", "gamma", "delta")
    assert command(path, "add", "alpha") == 0
    shown = StringIO()
    assert command(path, "raw-copy", "list", stdout=shown) == 0
    assert shown.getvalue() == "@alpha\n@gamma\n@delta\n"
    assert command(path, "raw-copy", "disable", "@GAMMA") == 0
    assert store.load().automatic_raw_copy_creators == ("alpha", "delta")
    assert store.load().monitored_creators == ("beta", "alpha")
    assert store.load().retention_protected_creators == ("protected",)
    assert store.load().retention_max_age_days == 30
    assert store.load().minimum_free_space_gib == 15
    for full in (True, False):
        assert load_service_configuration(path, validate_all=full).automatic_raw_copy_creators == ("alpha", "delta")
    assert main(["--config", str(path), "config", "set", "debug-tracebacks", "true"],
                stdout=StringIO()) == 0
    assert store.load().automatic_raw_copy_creators == ("alpha", "delta")
    shown = StringIO()
    assert main(["--config", str(path), "config", "show", "--json"], stdout=shown) == 0
    assert json.loads(shown.getvalue())["automatic_raw_copy_creators"] == ["alpha", "delta"]


def test_duplicate_enable_absent_disable_and_malformed_identity_preserve_bytes(tmp_path):
    path = tmp_path / "config.json"
    assert command(path, "raw-copy", "enable", "alpha") == 0
    before = path.read_bytes()
    for action, creator in (("enable", "@ALPHA"), ("disable", "absent"),
                            ("enable", "two creators"), ("disable", "http://bad")):
        assert command(path, "raw-copy", action, creator) == 1
        assert path.read_bytes() == before
    assert command(path, "raw-copy", "disable", "alpha") == 0
    assert "automatic_raw_copy_creators" not in json.loads(path.read_text())
    assert ConfigurationStore(path).load().automatic_raw_copy_creators == ()


@pytest.mark.parametrize("value", [None, True, "alpha", {}, [True], [7], ["Alpha"],
                                      ["@alpha"], ["alpha", "alpha"], [""], ["bad/"]])
def test_invalid_raw_copy_data_fails_all_loaders_and_mutations(tmp_path, value):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"schema_version": 1, "automatic_raw_copy_creators": value}))
    original = path.read_bytes()
    with pytest.raises(ConfigurationError):
        ConfigurationStore(path).load()
    for full in (True, False):
        with pytest.raises(ConfigurationError):
            load_service_configuration(path, validate_all=full)
    assert command(path, "raw-copy", "enable", "valid") == 1
    assert path.read_bytes() == original


@pytest.mark.parametrize("text", ['{',
    '{"schema_version":1,"automatic_raw_copy_creators":[],"automatic_raw_copy_creators":[]}'])
def test_malformed_and_duplicate_fields_are_rejected(tmp_path, text):
    path = tmp_path / "config.json"
    path.write_text(text)
    for full in (True, False):
        with pytest.raises(ConfigurationError):
            load_service_configuration(path, validate_all=full)
    assert command(path, "raw-copy", "enable", "alpha") == 1
    assert path.read_text() == text


def test_atomic_commands_keep_a_concurrently_committed_preference(tmp_path, monkeypatch):
    path = tmp_path / "config.json"
    store = ConfigurationStore(path)
    store.save(Configuration(monitored_creators=("alpha",)))
    update = ConfigurationStore.update

    def concurrent_update(self, transform):
        # Model a different command committing after dispatch, before the update lock.
        store.save(Configuration(monitored_creators=("beta",),
                                 automatic_raw_copy_creators=("other",)))
        return update(self, transform)

    monkeypatch.setattr(ConfigurationStore, "update", concurrent_update)
    assert command(path, "raw-copy", "enable", "alpha") == 0
    assert store.load().monitored_creators == ("beta",)
    assert store.load().automatic_raw_copy_creators == ("other", "alpha")


def test_serve_freezes_raw_copy_but_still_reloads_only_monitored_creators(tmp_path, monkeypatch):
    path = tmp_path / "config.json"
    store = ConfigurationStore(path)
    store.save(Configuration(monitored_creators=("alpha",), automatic_raw_copy_creators=("alpha",)))
    monkeypatch.delenv("TIKREC_TOKEN", raising=False)
    received = []

    def run(**options):
        assert options["automatic_raw_copy_creators"] == ("alpha",)
        store.save(Configuration(monitored_creators=("beta",), automatic_raw_copy_creators=("beta",)))
        assert options["creator_loader"]() == ("beta",)
        assert options["automatic_raw_copy_creators"] == ("alpha",)
        received.append(options)

    assert main(["--config", str(path), "serve"], service_runner=run, stdout=StringIO()) == 0
    assert len(received) == 1
    restarted = []
    assert main(["--config", str(path), "serve"], service_runner=lambda **kw: restarted.append(kw),
                stdout=StringIO()) == 0
    assert restarted[0]["automatic_raw_copy_creators"] == ("beta",)
