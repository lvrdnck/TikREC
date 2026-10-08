"""Real disposable Windows TCP acceptance, with exact socket/thread observations."""

import socket
from contextlib import contextmanager
from threading import Event, Thread, current_thread

from tests.service_http_helpers import compose, TOKEN


class ObservedSocket:
    """Delegate the exact accepted native socket; close faults precede native close."""

    def __init__(self, native):
        self.native, self.close_error, self.closes = native, None, []

    def __getattr__(self, name):
        return getattr(self.native, name)

    def close(self):
        """Record actual cleanup thread and retain the native object on injected failure."""
        self.closes.append(current_thread().name)
        if self.close_error is not None:
            raise self.close_error
        self.native.close()


class ObservedListener:
    """Keep real accept/select/listen behavior and wrap before ownership transfer."""

    def __init__(self, native, accepted):
        self.native, self.accepted = native, accepted
        self.next_error = None

    def __getattr__(self, name):
        return getattr(self.native, name)

    def accept(self):
        """Observe a real socket returned by the OS, never manufacture a connection."""
        native, address = self.native.accept()
        observed = ObservedSocket(native)
        observed.close_error, self.next_error = self.next_error, None
        self.accepted.append(observed)
        return observed, address


class Loopback:
    """Drive the server's real stdlib handle_request selection/accept/control path."""

    def __init__(self, server):
        self.server, self.accepted, self.clients = server, [], []
        self.release, self.entered = Event(), Event()
        self.calls = []
        self.listener = ObservedListener(server.socket, self.accepted)
        server.socket, server.timeout = self.listener, 0.1
        self.original_finish = server.finish_request

    def hold(self, request, address):
        """Hold actual native workers before real HTTP parsing and response writing."""
        self.calls.append(request)
        self.entered.set()
        assert self.release.wait(60), 'accept-loop worker release missing'
        self.original_finish(request, address)

    def connect(self, *, request=True):
        """Connect only to this ephemeral loopback listener, with bounded client I/O."""
        client = socket.socket()
        self.clients.append(client)
        client.settimeout(2)
        client.connect(self.server.server_address)
        if request:
            client.sendall(('GET /health HTTP/1.1\r\nHost: localhost\r\n'
                + 'Authorization: Bearer ' + TOKEN + '\r\n\r\n').encode())
        return client

    def handle(self):
        """Return the exact accept-loop error, permitting baseline defect observations."""
        try:
            self.server.handle_request()
        except BaseException as error:
            return error
        return None

    def read(self, client):
        """Read actual wire bytes through EOF, never construct a response in the fixture."""
        output = bytearray()
        while True:
            data = client.recv(65536)
            if not data:
                return bytes(output)
            output.extend(data)

    @contextmanager
    def serving(self):
        """Run the actual continuous select/accept loop and prove its native join."""
        errors = []
        def run():
            try:
                self.server.serve_forever(poll_interval=0.01)
            except BaseException as error:
                errors.append(error)
        worker = Thread(target=run, name='disposable-http-accept', daemon=False)
        worker.start()
        try:
            yield worker
        finally:
            self.server.shutdown()
            worker.join(5)
            assert not worker.is_alive() and not errors


@contextmanager
def loopback(case, tmp_path, **options):
    """Retire exact clients/listener/workers, independently repairing injected faults."""
    server, _ = compose(case, tmp_path, **options)
    wire = Loopback(server)
    case.releases.append(wire.release)
    try:
        yield wire
    finally:
        wire.release.set()
        for accepted in wire.accepted:
            accepted.close_error = None
        assert server.requests.join(5, closing=True), 'disposable request owners did not retire'
        server.server_close()
        # This separately labelled cleanup covers baseline sockets lost by the product.
        for accepted in wire.accepted:
            accepted.native.close()
            assert accepted.native.fileno() == -1
        for client in wire.clients:
            client.close()
            assert client.fileno() == -1
        assert server.socket.fileno() == -1
