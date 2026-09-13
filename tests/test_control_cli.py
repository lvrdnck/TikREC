"""Offline argparse and command dispatch tests for remote operation."""

import json
from io import BytesIO, StringIO
from urllib.error import HTTPError

import pytest

from tikrec.cli import _parser, main
from tikrec.control_cli import read_token


TOKEN = "test-secret-0123456789"


def test_serve_defaults_and_existing_commands(monkeypatch):
    monkeypatch.delenv("TIKREC_TOKEN", raising=False)
    calls = []
    assert main(["serve"], service_runner=lambda **kw: calls.append(kw), stdout=StringIO()) == 0
    assert calls == [{"host": "127.0.0.1", "port": 8765, "token": None}]
    parser = _parser()
    for command, args in [("live", ["page", "--output", "out.mp4"]),
                          ("record", ["flv", "--output", "out.mp4"]),
                          ("finalize", ["parts", "--output", "out.mp4"]),
                          ("resolve", ["page"]), ("validate", ["out.mp4"])]:
        assert parser.parse_args([command, *args]).command == command


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


@pytest.mark.parametrize("action", ["health", "status", "start", "stop"])
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
