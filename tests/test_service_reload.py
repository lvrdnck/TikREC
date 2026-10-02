"""CLI/service wiring applies only creators from later committed configuration."""

from io import StringIO
from unittest.mock import patch

from tikrec.cli import main
from tikrec.configuration import Configuration, ConfigurationError, ConfigurationStore
from tikrec.monitoring import CreatorMonitor
from tikrec.service import RecordingHTTPServer, serve
from tikrec.tiktok import TikTokOfflineError
from tests.test_automation_capacity import Slot
from tikrec.recording_manager import RecordingManager

import pytest


def test_serve_passes_reload_provider_with_default_or_explicit_path(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    monkeypatch.delenv("TIKREC_TOKEN", raising=False)
    selected = tmp_path / "TikREC" / "config.json"
    received = []
    assert main(["serve"], service_runner=lambda **kw: received.append(kw),
                stdout=StringIO()) == 0
    loader = received[0]["creator_loader"]
    with pytest.raises(ConfigurationError):
        loader()
    ConfigurationStore(selected).save(Configuration(monitored_creators=("added",)))
    assert loader() == ("added",)
    override = tmp_path / "explicit.json"
    ConfigurationStore(override).save(Configuration(monitored_creators=("explicit",)))
    assert main(["--config", str(override), "serve"],
                service_runner=lambda **kw: received.append(kw), stdout=StringIO()) == 0
    assert received[-1]["creator_loader"]() == ("explicit",)


def test_real_server_uses_public_config_changes_without_reloading_other_settings(tmp_path, monkeypatch):
    monkeypatch.delenv("TIKREC_TOKEN", raising=False)
    config = ConfigurationStore(tmp_path / "config.json")
    root = tmp_path / "recordings"
    root.mkdir()
    config.save(Configuration(output_directory=root, monitored_creators=("first",),
                              recovery_window_seconds=600, minimum_free_space_gib=10))
    def offline(_):
        raise TikTokOfflineError("offline", 4, "1")
    def factory(*args, **kwargs):
        monitor = CreatorMonitor(*args, resolver=offline, **kwargs)
        # Drive the real cycles deterministically; no network/worker timing is needed.
        monitor.start = lambda: None
        return monitor
    manager = RecordingManager((Slot(100), Slot(200)))
    def runner(**options):
        options["port"] = 0
        with patch("tikrec.service.CreatorMonitor", side_effect=factory):
            with RecordingHTTPServer(**options, manager=manager) as server:
                try:
                    server.monitor._poll_cycle()
                    assert main(["--config", str(config.path), "monitor", "add", "second"],
                                stdout=StringIO()) == 0
                    assert main(["--config", str(config.path), "monitor", "remove", "first"],
                                stdout=StringIO()) == 0
                    config.update(lambda _: Configuration(
                        output_directory=tmp_path / "different", monitored_creators=("second",),
                        recovery_window_seconds=60, minimum_free_space_gib=1024,
                        validation_mode="deep", debug_tracebacks=True,
                        retention_protected_creators=("first",), retention_max_age_days=1,
                    ))
                    server.monitor._poll_cycle()
                    assert [item["creator"] for item in server.monitor.snapshot()["creators"]] == ["second"]
                    assert server.admission._output_directory == root
                    assert server.storage_status.output_directory == root
                    assert server.storage_status.minimum_free_bytes == 10 * 1024**3
                    assert options["retry_policy"].window_seconds == 600
                    assert server.token is None
                    assert manager.health()["active_count"] == 0
                finally:
                    server.shutdown_components()
    assert main(["--config", str(config.path), "serve"],
                service_runner=runner, stdout=StringIO()) == 0


def test_serve_forwards_provider_to_http_server():
    loader = lambda: ("creator",)
    with patch("tikrec.service.RecordingHTTPServer") as server:
        server.return_value.__enter__.return_value.serve_forever.side_effect = KeyboardInterrupt
        serve(port=0, creator_loader=loader)
        assert server.call_args.kwargs["creator_loader"] is loader
