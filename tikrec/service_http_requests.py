"""Bounded original-thread request and SQLite cleanup ownership."""

import time
from threading import Event, RLock, Thread, get_ident

from .service_runtime_capture import retain_thread_after_error


class RequestOwners:
    """Retain non-daemon request threads until exact local cleanup and join succeed."""

    def __init__(self, server, thread_factory=Thread):
        self.server, self.factory = server, thread_factory
        self.lock, self.owners, self.closed = RLock(), {}, False
        self.accept_stopped, self.changed = False, Event()

    def _register(self, request):
        # Sixteen worker owners plus one accepted/refused socket reserve are finite.
        owner = {'retry': Event(), 'thread': None, 'request': request,
                 'kind': 'accepted', 'socket_closed': False, 'cleaned': False}
        self.owners[id(owner)] = owner
        return owner

    def _find(self, request):
        return next((owner for owner in self.owners.values()
                     if owner['request'] is request), None)

    def _can_accept(self):
        # A failed refusal close consumes the reserve. Leave new connections in the
        # finite OS backlog rather than accepting unlimited unretirable sockets.
        return (not self.accept_stopped and len(self.owners) < 17
                and all(owner['kind'] == 'worker' for owner in self.owners.values()))

    def accept(self, getter):
        """Register each native acceptance before returning it to the accept loop."""
        self.join(0)
        with self.lock:
            if not self._can_accept():
                raise BlockingIOError('request cleanup reserve unavailable')
            request, address = getter()
            self._register(request)
            return request, address

    def wait_capacity(self):
        """Pause a ready listener briefly when ownership prevents another accept."""
        self.join(0)
        with self.lock:
            if self._can_accept():
                return True
            self.changed.clear()
        self.changed.wait(0.05)
        return False

    def stop_accepting(self):
        """Fence native acceptance before checking the runtime shutdown barrier."""
        with self.lock:
            self.closed = self.accept_stopped = True
            self.changed.set()

    def _forget(self, owner):
        with self.lock:
            self.owners.pop(id(owner), None)
            self.changed.set()

    def _close(self, owner):
        # Workers call this only from their original thread. Socket-only owners
        # have never run a handler or borrowed SQLite and may be retried by join.
        try:
            self.server.shutdown_request(owner['request'])
        except BaseException as error:
            self.server.runtime.record_error(error)
            return False
        owner['socket_closed'] = True
        return True

    def _refuse(self, owner):
        with self.lock:
            owner['kind'] = 'socket'
            if self._close(owner):
                self._forget(owner)

    def handle_accepted(self, request, address):
        """Replace generic fallback cleanup after ownership has transferred."""
        with self.lock:
            owner = self._find(request)
        try:
            if self.server.verify_request(request, address):
                self.server.process_request(request, address)
            else:
                self._refuse(owner)
        except BaseException as error:
            if owner.get('primary') is not error:
                self.server.runtime.record_error(error)
            if owner['kind'] == 'accepted':
                self._refuse(owner)
            # A worker or previously attempted refusal keeps its exact socket.
            # Never invoke BaseServer's foreign-thread shutdown_request fallback.
            if not isinstance(error, Exception):
                raise

    def start(self, request, address):
        """Register before native start, retaining lost startup acknowledgement."""
        self.join(0)
        with self.lock:
            owner = self._find(request)
            if owner is None:
                # Direct process_request callers bypass the listener; enforce the
                # same finite reserve before accepting ownership from that caller.
                if (len(self.owners) >= 17
                        or any(o['kind'] != 'worker' for o in self.owners.values())):
                    raise RuntimeError('request ownership reserve unavailable')
                owner = self._register(request)
            if self.closed or sum(o['kind'] == 'worker' for o in self.owners.values()) >= 16:
                self._refuse(owner)
                return
            owner['kind'] = 'worker'
            try:
                worker = self.factory(target=self.run, args=(owner, request, address),
                    name='tikrec-isolated-http', daemon=False)
                owner['thread'] = worker
                worker.start()
            except BaseException as error:
                self.server.runtime.record_error(error)
                owner['primary'] = error
                if not retain_thread_after_error(self.server.runtime, owner['thread'], error):
                    # No request ran or borrowed SQLite, but the socket is still owned
                    # until its exact close succeeds; a secondary error cannot mask start.
                    self._refuse(owner)
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
                socket_pending = not self._close(owner)
            if not socket_pending and not self.current_borrowers():
                owner['cleaned'] = True
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
            if owner['kind'] == 'accepted':
                # Acceptance has not yet resolved verification/start/refusal.
                # Closing here could race a later native worker startup.
                continue
            if owner['kind'] == 'socket':
                if closing:
                    with self.lock:
                        if not owner['socket_closed'] and self._close(owner):
                            self._forget(owner)
                continue
            if closing:
                owner['retry'].set()
            worker = owner['thread']
            try:
                worker.join(max(0, deadline - time.monotonic()))
                retired = not worker.is_alive() and owner['cleaned'] and owner['socket_closed']
            except BaseException as error:
                self.server.runtime.record_error(error)
                retired = False
            if retired:
                self._forget(owner)
        with self.lock:
            return not self.owners
