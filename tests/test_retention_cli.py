"""Offline owner-facing retention configuration and read-only plan commands."""

import json
import os
import uuid
from io import StringIO
from pathlib import Path

import pytest

from tikrec.cli import main
from tikrec.configuration import Configuration, ConfigurationStore


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
    assert "files=unknown" in plain and "total bytes=unknown" in plain
    assert all(result["sessions"][0][field] is None for field in (
        "file_count", "flv_part_count", "final_output_bytes",
        "retained_parts_bytes", "total_file_bytes"))
    assert (directory / "session.json").read_bytes() == before


def test_plan_owner_fields_and_additive_json_schema(tmp_path: Path, monkeypatch) -> None:
    from tests.test_retention_plan import NOW, inspect, session
    import tikrec.retention_cli as cli

    root = tmp_path / "recordings"
    root.mkdir()
    parts = session(root, "alpha")
    session_id = json.loads((parts / "session.json").read_text())["session_id"]
    config_path = tmp_path / "config.json"
    ConfigurationStore(config_path).save(Configuration(
        output_directory=root, retention_max_age_days=1))
    original = cli.plan_retention
    monkeypatch.setattr(cli, "plan_retention", lambda root, config: original(
        root, config, clock=lambda: NOW, media_inspector=inspect))
    code, json_text, err = run(config_path, "retention", "plan", "--json")
    assert code == 0 and not err
    result = json.loads(json_text)
    item = result["sessions"][0]
    assert set(result) == {"root", "retention_max_age_days", "sessions"}
    assert {"parts_directory", "session_id", "creator", "ended_at",
            "output_path", "classification", "reason", "protected"} <= set(item)
    assert item["session_id"] == session_id and item["ended_at"] == 1010.0
    assert item["creator"] == "alpha" and item["protected"] is False
    assert item["file_count"] == len(list(parts.iterdir())) + 1
    assert item["flv_part_count"] == 1
    assert item["final_output_bytes"] == (root / "alpha.mp4").stat().st_size
    assert item["retained_parts_bytes"] == sum(p.stat().st_size for p in parts.iterdir())
    assert item["total_file_bytes"] == item["final_output_bytes"] + item["retained_parts_bytes"]

    code, plain, err = run(config_path, "retention", "plan", str(root))
    assert code == 0 and not err
    assert session_id in plain and "creator=alpha" in plain
    assert "ended=1970-01-01T00:16:50Z" in plain
    assert "eligible (age_threshold_reached)" in plain
    assert "protection=not protected" in plain
    assert str(parts) in plain and str(root / "alpha.mp4") in plain
    assert f"files={item['file_count']}" in plain
    assert f"FLV parts={item['flv_part_count']}" in plain
    assert f"final bytes={item['final_output_bytes']}" in plain
    assert f"retained-parts bytes={item['retained_parts_bytes']}" in plain
    assert f"total bytes={item['total_file_bytes']}" in plain

    ConfigurationStore(config_path).save(Configuration(
        output_directory=root, retention_max_age_days=1,
        retention_protected_creators=("alpha",)))
    code, protected, _ = run(config_path, "retention", "plan")
    assert code == 0 and "protected (protected_creator)" in protected
    assert "protection=protected (protected_creator)" in protected


def test_delete_parser_rejects_noncanonical_and_bulk_syntax(tmp_path):
    config = tmp_path / "config.json"
    valid = str(uuid.uuid4())
    for args in ((valid.upper(),), ("not-a-uuid",), (valid, str(tmp_path), "extra"),
                 (valid, "--yes")):
        out, err = StringIO(), StringIO()
        code = main(["--config", str(config), "retention", "delete", *args],
                    stdout=out, stderr=err)
        assert code == 2


@pytest.mark.skipif(os.name != "nt", reason="Windows preview tests")
def test_delete_interrupt_before_intent_returns_130(tmp_path):
    from tests.test_retention_delete_cli import Terminal, call
    from tests.test_retention_execute import fixture

    case = fixture(tmp_path)
    def interrupt():
        raise KeyboardInterrupt()
    code, _, err = call(case, stdin=Terminal(case[2] + "\n", interrupt))
    assert code == 130 and "interrupted before intent" in err
    assert case[1].exists() and not case[5].exists()
