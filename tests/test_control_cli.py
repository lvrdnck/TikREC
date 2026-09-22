"""Offline argparse and command dispatch tests for remote operation."""

import json
from io import BytesIO, StringIO
from urllib.error import HTTPError

import pytest

from tikrec.cli import _parser, main
from tikrec.control_cli import read_token
from tikrec.retry_policy import RetryPolicy


TOKEN = "test-secret-0123456789"


def test_serve_defaults_and_existing_commands(monkeypatch, tmp_path):
    monkeypatch.delenv("TIKREC_TOKEN", raising=False)
    calls = []
    config = tmp_path / "missing.json"
    assert main(["--config", str(config), "serve"],
                service_runner=lambda **kw: calls.append(kw), stdout=StringIO()) == 0
    assert calls == [{"host": "127.0.0.1", "port": 8765, "token": None,
                      "retry_policy": RetryPolicy(), "monitored_creators": (),
                      "output_directory": None}]
    parser = _parser()
    for command, args in [("live", ["page", "--output", "out.mp4"]),
                          ("record", ["flv", "--output", "out.mp4"]),
                          ("finalize", ["parts", "--output", "out.mp4"]),
                          ("resolve", ["page"]), ("validate", ["out.mp4"])]:
        assert parser.parse_args([command, *args]).command == command


def test_help_guides_normal_live_recording_and_advanced_sources(capsys):
    assert main(["--help"]) == 0
    top_level_help = capsys.readouterr().out
    assert "Normal use:" in top_level_help
    assert "tikrec live https://www.tiktok.com/@creator/live" in top_level_help
    assert "Configure an output directory for automatic naming" in top_level_help
    assert "normal use: record a public TikTok LIVE page" in top_level_help
    assert "advanced direct FLV/media URL, not a TikTok page" in top_level_help

    assert main(["live", "--help"]) == 0
    live_help = capsys.readouterr().out
    assert "public TikTok LIVE page URL" in live_help
    assert "tikrec live https://www.tiktok.com/@creator/live --output creator.mp4" in live_help
    assert "creator-YYYYMMDD-HHMMSS.mp4" in live_help

    assert main(["serve", "--help"]) == 0
    assert "--recovery-window-seconds" in capsys.readouterr().out

    assert main(["remote", "--help"]) == 0
    remote_help = capsys.readouterr().out
    assert "monitor-status" in remote_help and "recordings" in remote_help

    assert main(["remote", "stop", "--help"]) == 0
    assert "--session-id" in capsys.readouterr().out

    assert main(["monitor", "--help"]) == 0
    monitor_help = capsys.readouterr().out
    assert "service restarts" in monitor_help
    assert "does not contact TikTok or start recording" in monitor_help.replace("\n", " ")

    assert main(["record", "--help"]) == 0
    record_help = capsys.readouterr().out
    assert "advanced direct FLV/media URL" in record_help
    assert "does not accept a TikTok LIVE page URL" in record_help.replace("\n", " ")

    assert main(["resolve", "--help"]) == 0
    resolve_help = capsys.readouterr().out
    assert "public TikTok LIVE page URL" in resolve_help
    assert "direct FLV/media URL" in resolve_help


def test_non_loopback_requires_token_and_does_not_print_it(monkeypatch):
    monkeypatch.delenv("TIKREC_TOKEN", raising=False)
    stderr = StringIO()
    assert main(["serve", "--host", "100.100.1.2"], stderr=stderr,
                service_runner=lambda **kw: pytest.fail("must not run")) == 1
    assert "requires" in stderr.getvalue()
    monkeypatch.setenv("TIKREC_TOKEN", TOKEN)
    stdout = StringIO()
    calls = []
    assert main(["serve", "--host", "100.100.1.2"], stdout=stdout,
                service_runner=lambda **kw: calls.append(kw)) == 0
    assert calls[0]["token"] == TOKEN
    assert TOKEN not in stdout.getvalue()


@pytest.mark.parametrize(
    "action", ["health", "status", "recordings", "monitor-status", "start", "stop"]
)
def test_remote_commands(action, monkeypatch):
    monkeypatch.setenv("TIKREC_TOKEN", TOKEN)
    requests = []
    def opener(request, **kwargs):
        requests.append(request)
        return BytesIO(b'{"state": "completed", "output_path": "C:\\\\Videos\\\\out.mp4"}')
    argv = ["remote", action, "--server", "http://main-pc:8765"]
    if action == "start":
        argv += ["https://www.tiktok.com/@creator/live", "--output", r"C:\Videos\out.mp4"]
    stdout = StringIO()
    assert main(argv, remote_opener=opener, stdout=stdout) == 0
    assert json.loads(stdout.getvalue())["state"] == "completed"
    assert requests[0].get_header("Authorization") == f"Bearer {TOKEN}"
    assert TOKEN not in stdout.getvalue()


def test_remote_monitor_status_uses_dedicated_read_endpoint(monkeypatch):
    monkeypatch.delenv("TIKREC_TOKEN", raising=False)
    requests = []
    response = b'{"poll_interval_seconds":30.0,"creators":[]}'
    assert main(
        ["remote", "monitor-status", "--server", "http://main-pc:8765"],
        remote_opener=lambda request, **_: requests.append(request) or BytesIO(response),
        stdout=StringIO(),
    ) == 0
    assert requests[0].get_method() == "GET"
    assert requests[0].full_url == "http://main-pc:8765/monitoring"


def test_remote_start_raw_copy_is_explicit_opt_in(monkeypatch):
    monkeypatch.delenv("TIKREC_TOKEN", raising=False)
    requests = []
    def opener(request, **kwargs):
        requests.append(request)
        return BytesIO(b'{"state":"resolving"}')
    argv = ["remote", "start", "--server", "http://main-pc:8765", "--raw-copy",
            "https://www.tiktok.com/@creator/live", "--output", r"C:\Videos\out.mp4"]
    assert main(argv, remote_opener=opener, stdout=StringIO()) == 0
    assert json.loads(requests[0].data)["raw_copy"] is True


def test_remote_targeted_stop_dispatches_session_id(monkeypatch):
    monkeypatch.delenv("TIKREC_TOKEN", raising=False)
    requests = []
    session_id = "00000000-0000-0000-0000-000000000123"
    assert main([
        "remote", "stop", "--server", "http://main-pc",
        "--session-id", session_id,
    ], remote_opener=lambda request, **_: requests.append(request) or BytesIO(b'{}'),
        stdout=StringIO()) == 0
    assert json.loads(requests[0].data) == {"session_id": session_id}


def test_failed_job_status_returns_failure(monkeypatch):
    monkeypatch.delenv("TIKREC_TOKEN", raising=False)
    assert main(["remote", "status", "--server", "http://main-pc"], stdout=StringIO(),
                remote_opener=lambda *a, **k: BytesIO(b'{"state": "failed"}')) == 1


def test_remote_failure_is_safe_without_traceback(monkeypatch):
    monkeypatch.delenv("TIKREC_TOKEN", raising=False)
    def opener(request, **kwargs):
        raise HTTPError(request.full_url, 401, TOKEN, {}, BytesIO(TOKEN.encode()))
    stderr = StringIO()
    assert main(["remote", "stop", "--server", "http://main-pc"], remote_opener=opener,
                stderr=stderr) == 1
    assert "HTTP 401" in stderr.getvalue()
    assert "Traceback" not in stderr.getvalue() and TOKEN not in stderr.getvalue()


def test_token_file_overrides_environment_and_invalid_secrets_are_safe(tmp_path, monkeypatch):
    monkeypatch.setenv("TIKREC_TOKEN", "other-secret-123456")
    secret = tmp_path / "token.txt"
    secret.write_text(TOKEN + "\n")
    assert read_token(str(secret)) == TOKEN
    secret.write_text("bad secret")
    stderr = StringIO()
    assert main(["serve", "--token-file", str(secret)], stderr=stderr) == 1
    assert "bad secret" not in stderr.getvalue()
    with pytest.raises(ValueError, match="could not read"):
        read_token(str(tmp_path / "missing"))


def test_invalid_port_rejected_before_service_start(monkeypatch):
    monkeypatch.delenv("TIKREC_TOKEN", raising=False)
    assert main(["serve", "--port", "0"], stderr=StringIO(),
                service_runner=lambda **kw: pytest.fail("must not run")) == 1


def test_serve_recovery_window_precedence_and_lazy_configuration(tmp_path, monkeypatch):
    monkeypatch.delenv("TIKREC_TOKEN", raising=False)
    config = tmp_path / "config.json"
    config.write_text(json.dumps({
        "schema_version": 1, "recovery_window_seconds": 600,
    }), encoding="utf-8")
    calls = []
    assert main(["--config", str(config), "serve"],
                service_runner=lambda **kw: calls.append(kw), stdout=StringIO()) == 0
    assert calls[-1]["retry_policy"].window_seconds == 600
    assert main([
        "--config", str(config), "serve", "--recovery-window-seconds", "1200",
    ], service_runner=lambda **kw: calls.append(kw), stdout=StringIO()) == 0
    assert calls[-1]["retry_policy"].window_seconds == 1200

    config.write_text(json.dumps({
        "schema_version": 1,
        "validation_mode": "not-a-mode",
        "debug_tracebacks": "not-a-boolean",
        "recovery_window_seconds": "not-an-integer",
        "output_directory": str(tmp_path / "recordings"),
        "monitored_creators": ["first", "second"],
    }), encoding="utf-8")
    assert main(["--config", str(config), "serve"], stderr=StringIO(),
                service_runner=lambda **kw: pytest.fail("must not run")) == 1
    assert main([
        "--config", str(config), "serve", "--recovery-window-seconds", "60",
    ], service_runner=lambda **kw: calls.append(kw), stdout=StringIO()) == 0
    assert calls[-1]["retry_policy"].window_seconds == 60
    assert calls[-1]["monitored_creators"] == ("first", "second")
    assert calls[-1]["output_directory"] == tmp_path / "recordings"

    config.write_text(json.dumps({
        "schema_version": 1, "monitored_creators": ["NotCanonical"],
    }), encoding="utf-8")
    assert main([
        "--config", str(config), "serve", "--recovery-window-seconds", "60",
    ], stderr=StringIO(), service_runner=lambda **kw: pytest.fail("must not run")) == 1


def test_service_snapshots_configured_creators_at_startup(tmp_path, monkeypatch):
    monkeypatch.delenv("TIKREC_TOKEN", raising=False)
    config = tmp_path / "config.json"
    config.write_text(json.dumps({
        "schema_version": 1,
        "output_directory": str(tmp_path / "recordings"),
        "monitored_creators": ["first", "second"],
    }), encoding="utf-8")
    received = []

    def run(**kwargs):
        received.append((kwargs["monitored_creators"], kwargs["output_directory"]))
        config.write_text(json.dumps({
            "schema_version": 1, "monitored_creators": ["changed"],
        }), encoding="utf-8")

    assert main(["--config", str(config), "serve"], service_runner=run,
                stdout=StringIO()) == 0
    assert received == [(('first', 'second'), tmp_path / "recordings")]


def test_remote_shape_has_no_recovery_window_option() -> None:
    parser = _parser()
    with pytest.raises(SystemExit):
        parser.parse_args([
            "remote", "start", "--server", "http://main-pc",
            "https://www.tiktok.com/@creator/live", "--output", r"C:\Videos\out.mp4",
            "--recovery-window-seconds", "600",
        ])
