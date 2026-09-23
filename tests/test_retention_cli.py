"""Offline owner-facing retention configuration and read-only plan commands."""

import json
from io import StringIO
from pathlib import Path

import pytest

from tikrec.cli import main
from tikrec.configuration import ConfigurationStore


def run(path: Path, *args: str) -> tuple[int, str, str]:
    """Run one CLI action against an isolated user configuration."""
    out, err = StringIO(), StringIO()
    code = main(["--config", str(path), *args], stdout=out, stderr=err)
    return code, out.getvalue(), err.getvalue()


def test_protection_is_canonical_atomic_and_independent_of_monitoring(tmp_path: Path) -> None:
    config = tmp_path / "config.json"
    assert run(config, "retention", "protect", "@Alpha")[0] == 0
    assert run(config, "retention", "protected")[1] == "@alpha\n"
    assert run(config, "retention", "protect", "alpha")[0] == 1
    assert run(config, "retention", "unprotect", "beta")[0] == 1
    assert run(config, "monitor", "add", "alpha")[0] == 0
    assert run(config, "monitor", "remove", "alpha")[0] == 0
    assert ConfigurationStore(config).load().retention_protected_creators == ("alpha",)
    assert run(config, "retention", "unprotect", "ALPHA")[0] == 0
    assert run(config, "retention", "protected")[1] == "No protected creators.\n"


@pytest.mark.parametrize("value", ["0", "-1", "3651", "true", "1.5"])
def test_age_cli_rejects_invalid_values_without_replacing_config(tmp_path: Path,
                                                                  value: str) -> None:
    config = tmp_path / "config.json"
    assert run(config, "config", "set", "retention-max-age-days", "3650")[0] == 0
    before = config.read_bytes()
    assert run(config, "config", "set", "retention-max-age-days", value)[0] == 1
    assert config.read_bytes() == before


def test_age_show_set_unset_and_legacy_config(tmp_path: Path) -> None:
    config = tmp_path / "config.json"
    config.write_text('{"schema_version":1}', encoding="utf-8")
    assert ConfigurationStore(config).load().retention_max_age_days is None
    assert run(config, "config", "set", "retention-max-age-days", "1")[0] == 0
    shown = json.loads(run(config, "config", "show", "--json")[1])
    assert (shown["retention_max_age_days"], shown["retention_max_age_source"]) == (1, "configuration")
    assert run(config, "config", "unset", "retention-max-age-days")[0] == 0
    shown = json.loads(run(config, "config", "show", "--json")[1])
    assert shown["effective_retention_max_age_days"] is None
    assert shown["retention_max_age_source"] == "disabled"


@pytest.mark.parametrize("field,value", [
    ("retention_max_age_days", True), ("retention_max_age_days", 1.5),
    ("retention_max_age_days", 0), ("retention_max_age_days", 3651),
    ("retention_max_age_days", None),
    ("retention_protected_creators", ["Alpha"]),
    ("retention_protected_creators", ["alpha", "alpha"]),
    ("retention_protected_creators", None),
])
def test_corrupt_retention_configuration_fails_closed(tmp_path: Path, field, value) -> None:
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"schema_version": 1, field: value}), encoding="utf-8")
    assert run(config, "retention", "protected")[0] == 1
    assert run(config, "retention", "plan", str(tmp_path))[0] == 1


def test_plan_root_default_explicit_and_plain_json_parity(tmp_path: Path) -> None:
    config = tmp_path / "config.json"
    assert run(config, "retention", "plan")[0] == 1
    assert run(config, "config", "set", "output-directory", str(tmp_path))[0] == 0
    directory = tmp_path / "bad.parts"
    directory.mkdir()
    (directory / "session.json").write_text("{", encoding="utf-8")
    before = (directory / "session.json").read_bytes()
    code, json_text, _ = run(config, "retention", "plan", "--json")
    assert code == 0
    result = json.loads(json_text)
    assert result["sessions"][0]["reason"] == "evidence_conflict"
    code, plain, _ = run(config, "retention", "plan", str(tmp_path))
    assert code == 0 and "needs_attention (evidence_conflict)" in plain
    assert (directory / "session.json").read_bytes() == before
