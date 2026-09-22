"""Offline CLI tests for persistent monitored-creator configuration."""

import json
from io import StringIO
from pathlib import Path

import pytest

from tikrec.cli import main


def _run(path: Path, *arguments: str, stdout: StringIO | None = None,
         stderr: StringIO | None = None) -> int:
    return main(
        ["--config", str(path), "monitor", *arguments],
        resolver=lambda _: (_ for _ in ()).throw(AssertionError("must stay offline")),
        stdout=stdout or StringIO(), stderr=stderr or StringIO(),
    )


def test_list_with_absent_configuration_is_empty_and_does_not_create_file(
    tmp_path: Path,
) -> None:
    path = tmp_path / "config.json"
    stdout = StringIO()
    assert _run(path, "list", stdout=stdout) == 0
    assert stdout.getvalue() == "No monitored creators.\n"
    assert not path.exists()


def test_add_normalizes_supported_forms_and_list_preserves_order(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    values = (
        ("Creator_One", "creator_one"),
        ("@Creator.Two", "creator.two"),
        ("https://www.tiktok.com/@CreatorThree/live?lang=en", "creatorthree"),
    )
    for supplied, canonical in values:
        stdout = StringIO()
        assert _run(path, "add", supplied, stdout=stdout) == 0
        assert stdout.getvalue() == f"Added monitored creator: @{canonical}\n"
    document = json.loads(path.read_text(encoding="utf-8"))
    assert document == {
        "monitored_creators": [item[1] for item in values], "schema_version": 1,
    }
    stdout = StringIO()
    assert _run(path, "list", stdout=stdout) == 0
    assert stdout.getvalue() == "@creator_one\n@creator.two\n@creatorthree\n"


def test_duplicate_and_absent_remove_fail_without_changing_configuration(
    tmp_path: Path,
) -> None:
    path = tmp_path / "config.json"
    assert _run(path, "add", "Creator") == 0
    before = path.read_text(encoding="utf-8")
    stderr = StringIO()
    assert _run(path, "add", "@CREATOR", stderr=stderr) == 1
    assert "already monitored: @creator" in stderr.getvalue()
    assert path.read_text(encoding="utf-8") == before
    stderr = StringIO()
    assert _run(path, "remove", "absent", stderr=stderr) == 1
    assert "not monitored: @absent" in stderr.getvalue()
    assert path.read_text(encoding="utf-8") == before


def test_remove_accepts_live_url_and_preserves_remaining_order(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    for creator in ("first", "second", "third"):
        assert _run(path, "add", creator) == 0
    stdout = StringIO()
    assert _run(
        path, "remove", "https://www.tiktok.com/@SECOND/live", stdout=stdout
    ) == 0
    assert stdout.getvalue() == "Removed monitored creator: @second\n"
    assert json.loads(path.read_text(encoding="utf-8"))["monitored_creators"] == [
        "first", "third",
    ]


def test_add_preserves_every_existing_setting_without_output_directory_requirement(
    tmp_path: Path,
) -> None:
    path = tmp_path / "config.json"
    path.write_text(json.dumps({
        "schema_version": 1,
        "recovery_window_seconds": 600,
        "validation_mode": "deep",
        "debug_tracebacks": True,
    }), encoding="utf-8")
    assert _run(path, "add", "creator") == 0
    assert json.loads(path.read_text(encoding="utf-8")) == {
        "schema_version": 1,
        "recovery_window_seconds": 600,
        "validation_mode": "deep",
        "debug_tracebacks": True,
        "monitored_creators": ["creator"],
    }


def test_existing_config_mutations_preserve_monitored_creators(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    assert _run(path, "add", "creator") == 0
    assert main([
        "--config", str(path), "config", "set", "recovery-window-seconds", "600",
    ], stdout=StringIO()) == 0
    assert main([
        "--config", str(path), "config", "set", "debug-tracebacks", "true",
    ], stdout=StringIO()) == 0
    assert main([
        "--config", str(path), "config", "unset", "recovery-window-seconds",
    ], stdout=StringIO()) == 0
    assert json.loads(path.read_text(encoding="utf-8")) == {
        "schema_version": 1,
        "debug_tracebacks": True,
        "monitored_creators": ["creator"],
    }


@pytest.mark.parametrize("creator", [
    "", "@", "two creators", "creator/extra",
    "http://www.tiktok.com/@creator/live",
    "https://example.test/@creator/live",
])
def test_malformed_add_never_creates_configuration(
    tmp_path: Path, creator: str
) -> None:
    path = tmp_path / "config.json"
    stderr = StringIO()
    assert _run(path, "add", creator, stderr=stderr) == 1
    assert "creator" in stderr.getvalue()
    assert not path.exists()


def test_monitor_help_describes_service_restart_and_command_boundaries(capsys) -> None:
    for arguments in (("monitor", "--help"), ("monitor", "add", "--help"),
                      ("monitor", "remove", "--help"), ("monitor", "list", "--help")):
        assert main(list(arguments)) == 0
    output = capsys.readouterr().out
    help_text = " ".join(output.split())
    assert "Configure creators observed after the TikREC service restarts" in help_text
    assert "does not contact TikTok or start recording" in help_text
    assert "add one monitored creator" in help_text
    assert "remove one monitored creator" in help_text
    assert "list configured monitored creators" in help_text
