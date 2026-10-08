"""Bounded original-thread request and SQLite cleanup ownership."""

import time
from threading import Event, RLock, Thread, get_ident

from .service_runtime_capture import retain_thread_after_error


class RequestOwners:
    """Retain non-daemon request threads until exact local cleanup and join succeed."""

    def __init__(self, server, thread_factory=Thread):
        self.server, self.factory = server, thread_factory
        self.lock, self.owners, self.closed = RLock(), {}, False

    def start(self, request, address):
        """Register before native start, retaining lost startup acknowledgement."""
        self.join(0)
        with self.lock:
            if self.closed or len(self.owners) >= 16:
                self.server.shutdown_request(request)
                return
            owner = {'retry': Event(), 'thread': None}
            self.owners[id(owner)] = owner
            try:
                worker = self.factory(target=self.run, args=(owner, request, address),
                    name='tikrec-isolated-http', daemon=False)
                owner['thread'] = worker
                worker.start()
            except BaseException as error:
                self.server.runtime.record_error(error)
                if not retain_thread_after_error(self.server.runtime, owner['thread'], error):
                    # No request ran or borrowed SQLite, but the socket is still owned
                    # until its exact close succeeds; a secondary error cannot mask start.
                    owner.update(unstarted=True, request=request)
                    try:
                        self.server.shutdown_request(request)
                    except BaseException as secondary:
                        self.server.runtime.record_error(secondary)
                    else:
                        self.owners.pop(id(owner), None)
                raise

    def current_borrowers(self):
        """Include partial setup owners on this exact original SQLite thread."""
        registry = self.server.runtime.connections
        with registry.lock:
            return (any(c.thread == get_ident() for c in registry.connections.values())
                or any(thread == get_ident() and owner.connection is not None
                       for thread, owner in registry.partials))

    def run(self, owner, request, address):
        """Handle/disconnect then clean on this thread, waiting for explicit retry if needed."""
        runtime = self.server.runtime
        try:
            self.server.finish_request(request, address)
        except BaseException as error:
            runtime.record_error(error)
        finally:
            self.cleanup(owner, request)

    def cleanup(self, owner, request=None):
        """Retain a request or monitor borrower on its original thread for explicit cleanup."""
        runtime = self.server.runtime
        socket_pending = request is not None
        while True:
            try:
                runtime.connections.cleanup(runtime)
            except BaseException as error:
                runtime.record_error(error)
            if socket_pending:
                try:
                    self.server.shutdown_request(request)
                    socket_pending = False
                except BaseException as error:
                    runtime.record_error(error)
            if not socket_pending and not self.current_borrowers():
                break
            # A failed SQLite close cannot be retried by a foreign shutdown thread.
            # Keep the exact owner alive until a later explicit shutdown asks again.
            owner['retry'].wait()
            owner['retry'].clear()

    def join(self, timeout, *, closing=False):
        """Bound joins and report unresolved owners without discarding their objects."""
        deadline = time.monotonic() + timeout
        with self.lock:
            if closing:
                self.closed = True
            owners = tuple(self.owners.values())
        for owner in owners:
            if owner.get('unstarted'):
                if closing:
                    try:
                        self.server.shutdown_request(owner['request'])
                    except BaseException as error:
                        self.server.runtime.record_error(error)
                    else:
                        with self.lock:
                            self.owners.pop(id(owner), None)
                continue
            if closing:
                owner['retry'].set()
            worker = owner['thread']
            try:
                worker.join(max(0, deadline - time.monotonic()))
                retired = not worker.is_alive()
            except BaseException as error:
                self.server.runtime.record_error(error)
                retired = False
            if retired:
                with self.lock:
                    self.owners.pop(id(owner), None)
        with self.lock:
            return not self.owners
