"""HTTP handler tests use byte-backed fake sockets, never network access."""

import json
from io import BytesIO
from threading import Event
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from tikrec.capture import CaptureResult
from tikrec.recording import RecordingController
from tikrec.service import DEFAULT_HOST, RecordingHandler, RecordingHTTPServer, serve, validate_bind
from tikrec.retry_policy import RetryPolicy


TOKEN = "test-secret-0123456789"
PAGE = "https://www.tiktok.com/@creator/live"


def request(controller, method, path, body=None, *, token=None, headers=None, raw=None,
            monitor=None, admission=None, automation=None):
    data = json.dumps(body).encode() if raw is None and body is not None else (raw or b"")
    fields = {"Host": "localhost", "Content-Type": "application/json",
              "Content-Length": str(len(data)), **(headers or {})}
    raw_request = f"{method} {path} HTTP/1.1\r\n".encode()
    raw_request += "".join(f"{key}: {value}\r\n" for key, value in fields.items()).encode()
    raw_request += b"\r\n" + data

    class FakeSocket:
        def __init__(self):
            self.output = bytearray()

        def makefile(self, mode, buffering):
            return BytesIO(raw_request)

        def settimeout(self, seconds):
            assert seconds == 10

        def sendall(self, data):
            self.output.extend(data)

    connection = FakeSocket()
    monitoring = monitor or SimpleNamespace(snapshot=lambda: {"creators": []})
    policy = admission or SimpleNamespace(evaluate=lambda snapshot: snapshot)
    coordinator = automation or SimpleNamespace(snapshot=policy.evaluate)
    server = SimpleNamespace(
        controller=controller, monitor=monitoring, admission=policy,
        automation=coordinator, token=token,
    )
    RecordingHandler(connection, ("127.0.0.1", 1), server)
    head, response = bytes(connection.output).split(b"\r\n\r\n", 1)
    return int(head.split()[1]), json.loads(response)


def test_health_and_idle_status():
    controller = RecordingController()
    code, health = request(controller, "GET", "/health")
    assert code == 200 and health["service"] == "tikrec" and health["available"]
    assert request(controller, "GET", "/recording") == (200, {"state": "idle", "active": False})


def test_monitoring_status_comes_from_independent_component():
    snapshot = {"poll_interval_seconds": 30.0, "creators": [{"creator": "one"}]}
    monitor = SimpleNamespace(snapshot=lambda: snapshot)
    assert request(RecordingController(), "GET", "/monitoring", monitor=monitor) == (200, snapshot)


def test_monitoring_status_is_enriched_by_current_admission():
    snapshot = {"creators": [{"creator": "one", "state": "live"}]}
    enriched = {**snapshot, "minimum_free_bytes": 10 * 1024**3}
    calls = []
    monitor = SimpleNamespace(snapshot=lambda: snapshot)
    admission = SimpleNamespace(
        evaluate=lambda value: calls.append(value) or enriched
    )
    assert request(
        RecordingController(), "GET", "/monitoring",
        monitor=monitor, admission=admission,
    ) == (200, enriched)
    assert calls == [snapshot]


def test_monitoring_status_is_composed_by_automation():
    snapshot = {"cycle_count": 2, "creators": [{"creator": "one"}]}
    enriched = {**snapshot, "automation": {"operational": True}}
    calls = []
    monitor = SimpleNamespace(snapshot=lambda: snapshot)
    automation = SimpleNamespace(
        snapshot=lambda value: calls.append(value) or enriched
    )
    assert request(
        RecordingController(), "GET", "/monitoring",
        monitor=monitor, automation=automation,
    ) == (200, enriched)
    assert calls == [snapshot]


def test_http_start_conflict_status_and_stop_signal(tmp_path):
    entered = Event()
    received = []

    def capture(url, **kwargs):
        received.append(kwargs)
        kwargs["state"]("recording")
        entered.set()
        assert kwargs["stop_event"].wait(2)
        return CaptureResult((), kwargs["output_path"], True)

    controller = RecordingController(capture=capture)
    body = {"url": PAGE, "output": str(tmp_path / "out.mp4")}
    try:
        assert request(controller, "POST", "/recording/start", body)[0] == 202
        assert entered.wait(2)
        assert request(controller, "POST", "/recording/start", body)[0] == 409
        assert request(controller, "GET", "/recording")[1]["state"] == "recording"
        assert request(controller, "POST", "/recording/stop", {})[0] == 202
        assert received[0]["stop_event"].is_set()
    finally:
        controller.shutdown()
    code, status = request(controller, "GET", "/recording")
    assert code == 200 and status["state"] == "completed"
    assert status["final_output_path"] == body["output"]


def test_http_start_enables_co_located_raw_diagnostics(tmp_path):
    received, done = [], Event()
    def capture(url, **kwargs):
        received.append(kwargs)
        done.set()
        return CaptureResult((), None)
    controller = RecordingController(capture=capture)
    output = tmp_path / "diagnostic.mp4"
    try:
        code, status = request(controller, "POST", "/recording/start", {
            "url": PAGE, "output": str(output), "raw_copy": True,
        })
        assert code == 202 and status["raw_copy_enabled"] is True
        assert done.wait(2)
        controller._worker.join(2)
    finally:
        controller.shutdown()
    assert received[0]["raw_copy_dir"] == tmp_path / "diagnostic.parts"


def test_default_http_start_keeps_original_controller_call_shape():
    calls = []
    controller = SimpleNamespace(start=lambda url, output: (
        calls.append((url, output)) or {"state": "resolving"}
    ))
    assert request(controller, "POST", "/recording/start", {
        "url": PAGE, "output": r"C:\Videos\normal.mp4",
    })[0] == 202
    assert calls == [(PAGE, r"C:\Videos\normal.mp4")]


def test_api_stop_uses_real_live_finalization_path(tmp_path):
    from tikrec.live import capture_live
    from tests.test_live import stream

    entered = Event()

    def capture(url, **kwargs):
        def source(_):
            yield from stream()
            entered.set()
            assert kwargs["stop_event"].wait(2)
        def finalizer(parts, output):
            assert tuple(parts)[0].is_file()
            output.write_bytes(b"finalized")
            return output
        return capture_live(url, resolver=lambda _: "https://cdn.test/live.flv?secret=signed",
                            tag_source=source, finalizer=finalizer,
                            media_inspector=lambda _: None, **kwargs)

    controller = RecordingController(capture=capture)
    body = {"url": PAGE, "output": str(tmp_path / "out.mp4")}
    try:
        assert request(controller, "POST", "/recording/start", body)[0] == 202
        assert entered.wait(2)
        request(controller, "POST", "/recording/stop", {})
    finally:
        controller.shutdown()
    status = request(controller, "GET", "/recording")[1]
    assert status["state"] == "completed" and status["interrupted"]
    assert status["part_count"] == 1
    assert "signed" not in json.dumps(status)
    assert (tmp_path / "out.mp4").read_bytes() == b"finalized"
    assert (tmp_path / "out.parts/part-0001.flv").is_file()


@pytest.mark.parametrize(
    "path", ["/health", "/recording", "/monitoring", "/recording/start", "/recording/stop"]
)
def test_all_routes_require_configured_token(path):
    method = "POST" if path.endswith(("start", "stop")) else "GET"
    controller = RecordingController()
    code, response = request(controller, method, path, {}, token=TOKEN)
    assert code == 401 and TOKEN not in json.dumps(response)
    code, _ = request(controller, "GET", "/health", token=TOKEN,
                      headers={"Authorization": f"Bearer {TOKEN}"})
    assert code == 200


@pytest.mark.parametrize("body", [[], {}, {"url": PAGE, "output": "a", "executable": "evil"},
                                  {"url": PAGE, "output": "a", "expected_room_id": "123"},
                                  {"url": 1, "output": "a"},
                                  {"url": PAGE, "output": "a", "raw_copy": 1},
                                  {"url": PAGE, "output": "a", "raw_copy": "yes"}])
def test_invalid_start_shape_is_rejected(body):
    assert request(RecordingController(), "POST", "/recording/start", body)[0] == 400


def test_body_limits_and_browser_origin():
    controller = RecordingController()
    assert request(controller, "POST", "/recording/start", raw=b"broken")[0] == 400
    assert request(controller, "POST", "/recording/start", raw=b"x" * 8193)[0] == 413
    assert request(controller, "POST", "/recording/stop", {},
                   headers={"Content-Type": "text/plain"})[0] == 415
    assert request(controller, "POST", "/recording/stop", {},
                   headers={"Origin": "https://evil.test"})[0] == 403
    assert request(controller, "GET", "/monitoring",
                   headers={"Origin": "https://evil.test"})[0] == 403
    assert request(controller, "POST", "/recording/stop", {"command": "kill"})[0] == 400
    assert request(controller, "GET", "/files")[0] == 404


def test_bind_defaults_and_explicit_remote_security():
    assert DEFAULT_HOST == "127.0.0.1"
    assert validate_bind(DEFAULT_HOST, None) == DEFAULT_HOST
    assert validate_bind("localhost", None) == DEFAULT_HOST
    assert validate_bind("::1", None) == "::1"
    for host in ("0.0.0.0", "100.100.1.2", "192.168.1.2"):
        with pytest.raises(ValueError, match="requires"):
            validate_bind(host, None)
        assert validate_bind(host, TOKEN) == host
    with pytest.raises(ValueError):
        validate_bind("main-pc", TOKEN)
    with pytest.raises(ValueError, match="token must"):
        validate_bind(DEFAULT_HOST, "short")


def test_server_constructs_loopback_by_default_without_opening_socket(tmp_path):
    # Default persistence must never inspect the developer's real job or open its LIVE.
    with patch("tikrec.service.ThreadingHTTPServer.__init__", return_value=None) as constructor:
        with patch("tikrec.service.default_job_state_path", return_value=tmp_path / "job.json"):
            server = RecordingHTTPServer()
    assert constructor.call_args.args[0] == ("127.0.0.1", 8765)
    assert server.controller.status()["state"] == "idle"
    assert server.automation._store.path == tmp_path / "automation.json"


def test_server_supplies_selected_policy_to_default_controller(tmp_path):
    policy = RetryPolicy(window_seconds=600)
    with patch("tikrec.service.ThreadingHTTPServer.__init__", return_value=None):
        with patch("tikrec.service.default_job_state_path", return_value=tmp_path / "job.json"):
            server = RecordingHTTPServer(retry_policy=policy)
    assert server.controller._retry_policy is policy


def test_server_owns_monitor_start_stop_and_join():
    calls = []
    controller = SimpleNamespace(
        health=lambda: {"available": True},
        shutdown=lambda: calls.append("controller shutdown"),
    )
    monitor = SimpleNamespace(
        start=lambda: calls.append("monitor start"),
        stop=lambda: calls.append("monitor stop"),
        join=lambda: calls.append("monitor join"),
    )
    automation = SimpleNamespace(stop=lambda: calls.append("automation stop"))
    with patch("tikrec.service.ThreadingHTTPServer.__init__", return_value=None):
        server = RecordingHTTPServer(
            controller=controller, monitor=monitor, automation=automation
        )
    server.shutdown_components()
    assert calls == [
        "monitor start", "automation stop", "monitor stop",
        "controller shutdown", "monitor join",
    ]


def test_server_builds_monitor_from_startup_creator_snapshot():
    monitor = SimpleNamespace(start=lambda: None, stop=lambda: None, join=lambda: None)
    controller = SimpleNamespace(health=lambda: {"available": True}, shutdown=lambda: None)
    callback = lambda snapshot: None
    automation = SimpleNamespace(cycle_completed=callback, stop=lambda: None)
    with patch("tikrec.service.ThreadingHTTPServer.__init__", return_value=None):
        with patch("tikrec.service.CreatorMonitor", return_value=monitor) as factory:
            server = RecordingHTTPServer(
                controller=controller, automation=automation,
                monitored_creators=("first", "second")
            )
    factory.assert_called_once_with(
        ("first", "second"), cycle_completed=callback
    )
    server.shutdown_components()


def test_server_builds_admission_from_startup_output_snapshot(tmp_path):
    monitor = SimpleNamespace(start=lambda: None, stop=lambda: None, join=lambda: None)
    controller = SimpleNamespace(health=lambda: {"available": True}, shutdown=lambda: None)
    admission = SimpleNamespace(evaluate=lambda snapshot: snapshot)
    automation = SimpleNamespace(stop=lambda: None)
    with patch("tikrec.service.ThreadingHTTPServer.__init__", return_value=None):
        with patch("tikrec.service.RecordingAdmission", return_value=admission) as factory:
            server = RecordingHTTPServer(
                controller=controller, monitor=monitor, automation=automation,
                output_directory=tmp_path
            )
    assert factory.call_args.args == (tmp_path, controller.health)
    assert server.admission is admission
    server.shutdown_components()


def test_service_interrupt_shuts_down_controller_without_killing_worker():
    calls = []

    class FakeServer:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            calls.append("closed server")

        def serve_forever(self):
            raise KeyboardInterrupt()

        def shutdown_components(self):
            calls.append("cooperative shutdown")

    with patch("tikrec.service.RecordingHTTPServer", return_value=FakeServer()):
        serve()
    assert calls == ["cooperative shutdown", "closed server"]
