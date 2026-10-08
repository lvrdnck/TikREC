"""Actual HTTP parsing/serialization on byte-backed sockets and isolated Windows state."""

import json
from dataclasses import replace
from io import BytesIO
from pathlib import Path
from threading import Event
from types import SimpleNamespace
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit

from tikrec.admission import RecordingAdmission
from tikrec.automation import AutomationCoordinator
from tikrec.automation_state import AutomationStateStore
from tikrec.monitoring import CreatorMonitor
from tikrec.remote import RemoteClient
from tikrec.service_http_runtime import IsolatedRecordingHTTPServer


TOKEN = 'test-secret-0123456789'


class WireSocket:
    """Exercise BaseHTTPRequestHandler's actual request/response byte format offline."""

    def __init__(self, raw, *, disconnect=False):
        self.raw, self.output = raw, bytearray()
        self.closed, self.sent = Event(), Event()
        self.disconnect = disconnect

    def makefile(self, mode, buffering):
        """Supply real HTTP bytes to the original header/body parser."""
        return BytesIO(self.raw)

    def settimeout(self, value):
        """Assert the inherited request read bound stays in force."""
        assert value == 10

    def sendall(self, data):
        """Capture exact response bytes or lose the post-acceptance acknowledgement."""
        if self.disconnect and self.output:
            self.sent.set()
            raise BrokenPipeError('fixture disconnect secret')
        self.output.extend(data)
        if b'\r\n\r\n' in self.output:
            head, body = bytes(self.output).split(b'\r\n\r\n', 1)
            sizes = [int(line.split(b':')[1]) for line in head.split(b'\r\n')
                     if line.startswith(b'Content-Length:')]
            if sizes and len(body) >= sizes[0]:
                self.sent.set()

    def shutdown(self, how):
        """The real server closes the addressed disposable connection."""

    def close(self):
        """Signal socket retirement independently of SQLite ownership."""
        self.closed.set()


def dispatch(server, method, route, body=None, *, headers=None, disconnect=False, raw=None):
    """Launch a real tracked request thread over a byte-backed connection."""
    data = json.dumps(body).encode() if body is not None else b''
    fields = {'Host': 'localhost', 'Authorization': 'Bearer ' + TOKEN,
        'Content-Type': 'application/json', 'Content-Length': str(len(data)), **(headers or {})}
    request = (f'{method} {route} HTTP/1.1\r\n'
        + ''.join(f'{key}: {value}\r\n' for key, value in fields.items()) + '\r\n').encode() + data
    connection = WireSocket(request if raw is None else raw, disconnect=disconnect)
    server.process_request(connection, ('127.0.0.1', 1))
    assert connection.sent.wait(15), 'HTTP response not received'
    return connection


def response(connection):
    """Decode the actual wire response, never manufacture transport status."""
    head, body = bytes(connection.output).split(b'\r\n\r\n', 1)
    return int(head.split()[1]), json.loads(body)


def client_for(server):
    """Drive RemoteClient serialization through actual isolated request handlers."""
    def opener(request, **_):
        body = None if request.data is None else json.loads(request.data)
        connection = dispatch(server, request.get_method(), urlsplit(request.full_url).path,
            body, headers=dict(request.header_items()))
        code, value = response(connection)
        content = json.dumps(value).encode()
        if code >= 400:
            raise HTTPError(request.full_url, code, 'fixture', {}, BytesIO(content))
        return BytesIO(content)
    return RemoteClient('http://127.0.0.1', token=TOKEN, opener=opener)


def compose(case, tmp_path, *, runtime=None, raw_creators=(), **options):
    """Supply every policy component/state explicitly, with no default paths."""
    runtime = runtime or case.build()
    original = runtime.observations
    rooms = {}
    def supplied(bridge):
        # HTTP callers cannot supply expected_room_id; the injected resolver proves it.
        name = Path(bridge.intent.output_path).stem
        room = bridge.intent.expected_room or rooms.setdefault(name, str(1000 + len(rooms)))
        view = SimpleNamespace(intent=replace(bridge.intent, expected_room=room),
                               stop_event=bridge.stop_event)
        return original(view)
    runtime.observations = supplied
    admission = RecordingAdmission(runtime.root, runtime.health, storage_status=runtime.storage)
    automation = AutomationCoordinator(runtime, admission,
        AutomationStateStore(tmp_path / 'explicit-automation.json'),
        automatic_raw_copy_creators=raw_creators)
    monitor = CreatorMonitor((), cycle_completed=automation.cycle_completed)
    server = IsolatedRecordingHTTPServer(port=0, runtime=runtime, admission=admission,
        automation=automation, monitor=monitor, token=TOKEN, request_grace=0.5, **options)
    return server, client_for(server)


def start_http(client, runtime, name, *, creator='example.creator', raw=False):
    """Start through the normal public request shape, never internal room controls."""
    return client.start('https://www.tiktok.com/@' + creator + '/live',
        str(runtime.root / (name + '.mp4')), raw_copy=raw)
