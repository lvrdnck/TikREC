"""Offline configuration CLI and local recording precedence tests."""

import json
from datetime import datetime
from io import BytesIO, StringIO
from pathlib import Path

from tikrec.capture import CaptureResult
from tikrec.cli import main


def _capture_calls():
    calls = []

    def capture(url, **kwargs):
        calls.append((url, kwargs))
        return CaptureResult((), Path(kwargs["output_path"]), False)

    return calls, capture


def test_config_path_does_not_load_malformed_file(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text("{", encoding="utf-8")
    stdout = StringIO()
    assert main(["--config", str(path), "config", "path"], stdout=stdout) == 0
    assert stdout.getvalue() == f"{path}\n"


def test_config_show_reports_missing_file_and_effective_cwd(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "config.json"
    stdout = StringIO()
    assert main(["--config", str(path), "config", "show", "--json"], stdout=stdout) == 0
    result = json.loads(stdout.getvalue())
    assert result == {
        "config_path": str(path),
        "effective_output_directory": str(tmp_path),
        "exists": False,
        "output_directory": None,
        "output_directory_source": "current_working_directory",
        "effective_recovery_window_seconds": 900,
        "recovery_window_seconds": None,
        "recovery_window_source": "built_in_default",
    }


def test_config_set_show_and_unset_preserve_valid_document(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    recordings = tmp_path / "recordings"
    assert main([
        "--config", str(path), "config", "set", "output-directory", str(recordings)
    ], stdout=StringIO()) == 0
    assert not recordings.exists()
    stdout = StringIO()
    assert main(["--config", str(path), "config", "show", "--json"], stdout=stdout) == 0
    result = json.loads(stdout.getvalue())
    assert result["exists"] is True
    assert result["output_directory"] == str(recordings)
    assert result["output_directory_source"] == "configuration"
    assert main([
        "--config", str(path), "config", "set", "recovery-window-seconds", "600"
    ], stdout=StringIO()) == 0
    stdout = StringIO()
    assert main(["--config", str(path), "config", "show", "--json"], stdout=stdout) == 0
    result = json.loads(stdout.getvalue())
    assert result["recovery_window_seconds"] == 600
    assert result["effective_recovery_window_seconds"] == 600
    assert result["recovery_window_source"] == "configuration"
    assert main([
        "--config", str(path), "config", "unset", "output-directory"
    ], stdout=StringIO()) == 0
    assert json.loads(path.read_text(encoding="utf-8")) == {
        "recovery_window_seconds": 600, "schema_version": 1,
    }
    assert main([
        "--config", str(path), "config", "unset", "recovery-window-seconds"
    ], stdout=StringIO()) == 0
    assert json.loads(path.read_text(encoding="utf-8")) == {"schema_version": 1}


def test_config_recovery_window_unset_preserves_other_setting(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    recordings = tmp_path / "recordings"
    path.write_text(json.dumps({
        "schema_version": 1, "output_directory": str(recordings),
        "recovery_window_seconds": 60,
    }), encoding="utf-8")
    assert main([
        "--config", str(path), "config", "unset", "recovery-window-seconds"
    ], stdout=StringIO()) == 0
    assert json.loads(path.read_text(encoding="utf-8")) == {
        "output_directory": str(recordings), "schema_version": 1,
    }


def test_config_recovery_window_rejects_invalid_values(tmp_path: Path) -> None:
    for value in ("59", "3601", "60.0", "true", "0", "-1"):
        assert main([
            "--config", str(tmp_path / "config.json"), "config", "set",
            "recovery-window-seconds", value,
        ], stderr=StringIO()) == 1


def test_config_mutation_does_not_overwrite_malformed_document(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    content = '{"schema_version": 1, "typo": true}'
    path.write_text(content, encoding="utf-8")
    stderr = StringIO()
    assert main([
        "--config", str(path), "config", "set", "output-directory", str(tmp_path)
    ], stdout=StringIO(), stderr=stderr) == 1
    assert "unknown or invalid" in stderr.getvalue()
    assert path.read_text(encoding="utf-8") == content


def test_malformed_config_fails_actionably_but_version_remains_available(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text("{", encoding="utf-8")
    stderr = StringIO()
    assert main(["--config", str(path), "record", "source", "--output", "out.mp4"],
                capture=lambda *a, **k: None, stderr=stderr) == 1
    assert "invalid configuration" in stderr.getvalue()
    stdout = StringIO()
    assert main(["--config", str(path), "--version"], stdout=stdout) == 0


def test_absolute_record_output_does_not_load_or_relocate_from_bad_config(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text("{", encoding="utf-8")
    output = tmp_path / "absolute.mp4"
    calls, capture = _capture_calls()
    assert main(["--config", str(path), "record", "source", "--output", str(output)],
                capture=capture, stdout=StringIO()) == 0
    assert calls[0][1]["output_path"] == output


def test_relative_record_output_uses_configured_directory(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    recordings = tmp_path / "recordings"
    assert main(["--config", str(path), "config", "set", "output-directory", str(recordings)],
                stdout=StringIO()) == 0
    calls, capture = _capture_calls()
    assert main(["--config", str(path), "record", "source", "--output", "creator.mp4"],
                capture=capture, stdout=StringIO()) == 0
    assert calls[0][1]["output_path"] == recordings / "creator.mp4"
    assert calls[0][1]["parts_directory"] == recordings / "creator.parts"


def test_relative_live_output_uses_configured_directory(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    recordings = tmp_path / "recordings"
    assert main(["--config", str(path), "config", "set", "output-directory", str(recordings)],
                stdout=StringIO()) == 0
    calls, live_capture = _capture_calls()
    assert main([
        "--config", str(path), "live", "https://www.tiktok.com/@creator/live",
        "--output", "creator.mp4",
    ], live_capture=live_capture, stdout=StringIO()) == 0
    assert calls[0][1]["output_path"] == recordings / "creator.mp4"
    assert calls[0][1]["parts_directory"] == recordings / "creator.parts"


def test_local_live_recovery_window_precedence_and_lazy_configuration(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text(json.dumps({
        "schema_version": 1, "recovery_window_seconds": 600,
    }), encoding="utf-8")
    output = tmp_path / "out.mp4"
    calls, live_capture = _capture_calls()
    assert main([
        "--config", str(path), "live", "https://www.tiktok.com/@creator/live",
        "--output", str(output),
    ], live_capture=live_capture, stdout=StringIO()) == 0
    assert calls[-1][1]["retry_policy"].window_seconds == 600

    assert main([
        "--config", str(path), "live", "https://www.tiktok.com/@creator/live",
        "--output", str(output), "--recovery-window-seconds", "1200",
    ], live_capture=live_capture, stdout=StringIO()) == 0
    assert calls[-1][1]["retry_policy"].window_seconds == 1200

    path.write_text("{", encoding="utf-8")
    stderr = StringIO()
    assert main([
        "--config", str(path), "live", "https://www.tiktok.com/@creator/live",
        "--output", str(output),
    ], live_capture=live_capture, stderr=stderr) == 1
    assert "invalid configuration" in stderr.getvalue()
    assert main([
        "--config", str(path), "live", "https://www.tiktok.com/@creator/live",
        "--output", str(output), "--recovery-window-seconds", "60",
    ], live_capture=live_capture, stdout=StringIO()) == 0
    assert calls[-1][1]["retry_policy"].window_seconds == 60


def test_local_live_uses_built_in_recovery_window(tmp_path: Path) -> None:
    calls, live_capture = _capture_calls()
    assert main([
        "--config", str(tmp_path / "missing.json"), "live",
        "https://www.tiktok.com/@creator/live", "--output", str(tmp_path / "out.mp4"),
    ], live_capture=live_capture, stdout=StringIO()) == 0
    assert calls[0][1]["retry_policy"].window_seconds == 900


def test_live_without_output_uses_safe_automatic_name_without_resolving(
    tmp_path: Path,
) -> None:
    path = tmp_path / "config.json"
    recordings = tmp_path / "recordings"
    assert main(["--config", str(path), "config", "set", "output-directory", str(recordings)],
                stdout=StringIO()) == 0
    assert main([
        "--config", str(path), "config", "set", "recovery-window-seconds", "600"
    ], stdout=StringIO()) == 0
    calls, live_capture = _capture_calls()
    assert main([
        "--config", str(path), "live",
        "https://www.tiktok.com/@creator/live?token=must-not-appear",
    ], live_capture=live_capture,
       resolver=lambda _: (_ for _ in ()).throw(AssertionError("must not resolve for naming")),
       naming_clock=lambda: datetime(2026, 9, 21, 18, 45, 0),
       stdout=StringIO()) == 0
    assert calls[0][1]["output_path"] == recordings / "creator-20260921-184500.mp4"
    assert calls[0][1]["parts_directory"] == recordings / "creator-20260921-184500.parts"
    assert calls[0][1]["retry_policy"].window_seconds == 600
    assert "token" not in str(calls[0][1]["output_path"])


def test_explicit_live_output_wins_over_automatic_name(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    recordings = tmp_path / "recordings"
    assert main(["--config", str(path), "config", "set", "output-directory", str(recordings)],
                stdout=StringIO()) == 0
    calls, live_capture = _capture_calls()
    assert main([
        "--config", str(path), "live", "https://www.tiktok.com/@creator/live",
        "--output", "chosen.mp4",
    ], live_capture=live_capture,
       naming_clock=lambda: (_ for _ in ()).throw(AssertionError("clock must not run")),
       stdout=StringIO()) == 0
    assert calls[0][1]["output_path"] == recordings / "chosen.mp4"


def test_live_without_output_requires_configured_directory(tmp_path: Path) -> None:
    calls, live_capture = _capture_calls()
    stderr = StringIO()
    assert main([
        "--config", str(tmp_path / "missing.json"), "live",
        "https://www.tiktok.com/@creator/live",
    ], live_capture=live_capture, stderr=stderr) == 1
    assert calls == []
    assert "config set output-directory" in stderr.getvalue()
    assert "provide --output" in stderr.getvalue()


def test_missing_config_keeps_relative_record_output_unchanged(tmp_path: Path) -> None:
    calls, capture = _capture_calls()
    assert main([
        "--config", str(tmp_path / "missing.json"), "record", "source",
        "--output", "creator.mp4",
    ], capture=capture, stdout=StringIO()) == 0
    assert calls[0][1]["output_path"] == Path("creator.mp4")


def test_finalize_remote_and_recover_paths_are_not_reinterpreted(tmp_path: Path) -> None:
    config = tmp_path / "config.json"
    config.write_text("{", encoding="utf-8")
    # These command surfaces must not consult a malformed local recording config.
    stderr = StringIO()
    assert main(["--config", str(config), "finalize", "missing", "--output", "relative.mp4"],
                stderr=stderr) == 1
    assert "parts directory does not exist" in stderr.getvalue()
    stdout = StringIO()
    assert main([
        "--config", str(config), "recover", str(tmp_path / "missing")
    ], recovery_discoverer=lambda _: [], stdout=stdout) == 0
    remote = StringIO()
    assert main([
        "--config", str(config), "remote", "health", "--server", "http://main-pc"
    ], remote_opener=lambda *a, **k: BytesIO(b'{"state":"idle"}'), stdout=remote) == 0
    assert json.loads(remote.getvalue()) == {"state": "idle"}


def test_config_help_is_available_without_reading_configuration(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text("{", encoding="utf-8")
    assert main(["--config", str(path), "config", "--help"]) == 0


def test_live_help_explains_optional_automatic_output(capsys) -> None:
    assert main(["live", "--help"]) == 0
    help_text = capsys.readouterr().out
    assert "omit for configured automatic naming" in help_text
    assert "creator-YYYYMMDD-HHMMSS.mp4" in help_text
    assert "--recovery-window-seconds" in help_text


def test_direct_record_still_requires_output() -> None:
    assert main(["record", "https://cdn.test/live.flv"]) == 2
