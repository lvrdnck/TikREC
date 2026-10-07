"""Runtime-only SQLite lifetime observation; journal identity and guards stay original."""

from threading import RLock, get_ident

from .session_journal_manifest_fence import ManifestFenceConnection
from .session_journal_types import require


class RuntimeConnection:
    """Delegate the exact borrowed connection and retain an unconfirmed close."""

    def __init__(self, registry, connection):
        self.registry, self.raw = registry, connection
        self.owner, self.thread, self.failed = ManifestFenceConnection(connection), get_ident(), False

    def __getattr__(self, name):
        return getattr(self.raw, name)

    def close(self):
        """Observe the actual close result without changing commit or rollback behavior."""
        if self.owner.connection is None:
            return
        try:
            self.raw.close()
        except BaseException:
            self.failed = True
            raise
        self.owner.connection = None
        self.registry.forget(self)


class RuntimeConnections:
    """Track live local SQLite owners without another catalog or durable authority."""

    def __init__(self, journal):
        self.journal, self.original = journal, journal._connect
        previous = getattr(self.original, '__self__', None)
        if isinstance(previous, RuntimeConnections) and not previous.enabled:
            self.original = previous.original
        self.lock, self.connections, self.partials, self.opening = RLock(), {}, [], 0
        self.enabled = False
        self.closing = False

    def install(self):
        """Instrument only this explicitly supplied instance after native authority acquisition."""
        self.enabled = True
        self.journal._connect = self.connect

    def restore(self):
        """Restore the original connector only after every runtime borrower retired."""
        require(not self.has_ownership(), 'SQLite borrowers still protect catalog lifetime')
        self.enabled = False
        if getattr(self.journal._connect, '__self__', None) is self:
            self.journal._connect = self.original

    def seal(self):
        """Fence new borrowers atomically with the last ownership check before native close."""
        with self.lock:
            require(not self.has_ownership(), 'SQLite borrowers still protect catalog lifetime')
            self.closing = True

    def connect(self):
        """Register before caller BEGIN and retain partial setup owners on failure."""
        if not self.enabled:
            return self.original()
        with self.lock:
            require(not self.closing, 'runtime journal is closing')
            require(len(self.connections) + len(self.partials) + self.opening < 32,
                    'runtime SQLite ownership bound reached')
            self.opening += 1
        try:
            connection = RuntimeConnection(self, self.original())
            with self.lock:
                self.connections[id(connection)] = connection
            return connection
        except BaseException as error:
            partial = getattr(error, 'manifest_fence_owner', None)
            if partial is not None and partial.connection is not None:
                with self.lock:
                    self.partials.append((get_ident(), partial))
            raise
        finally:
            with self.lock:
                self.opening -= 1

    def forget(self, connection):
        """Retire only the same known-closed borrowed object."""
        with self.lock:
            self.connections.pop(id(connection), None)

    def has_ownership(self):
        """Include setup in flight and failed closes, independent of Python GC."""
        with self.lock:
            self.partials[:] = [(thread, owner) for thread, owner in self.partials if owner.connection is not None]
            return bool(self.connections or self.partials or self.opening)

    def claimed(self, runtime):
        """Keep accepted settlement/recovery reader cleanup with its original owner."""
        readers = []
        adapter = runtime.current
        if adapter is not None:
            if adapter.capability is not None:
                readers.extend(adapter.capability.readers)
            manifest = getattr(adapter.coordinator, 'manifest_owner', None)
            if manifest is not None and manifest.fence_owner is not None:
                readers.append(manifest.fence_owner)
        for owner in tuple(runtime.authority._recovery_owners.values()):
            readers.extend(owner.readers)
        connections = set()
        for reader in readers:
            connection, visited = reader.connection, set()
            while connection is not None and id(connection) not in visited:
                visited.add(id(connection))
                if isinstance(connection, RuntimeConnection):
                    connections.add(id(connection))
                connection = getattr(connection, 'raw', None)
        return connections, {id(reader) for reader in readers}

    def failed(self, runtime):
        """Report generic control uncertainty separately from accepted attempt owners."""
        claimed, readers = self.claimed(runtime)
        with self.lock:
            return (any(c.failed and id(c) not in claimed for c in self.connections.values())
                or any(owner.connection is not None and id(owner) not in readers for _, owner in self.partials))

    def cleanup(self, runtime):
        """Close generic borrowers only on their original thread, preserving actual errors."""
        claimed, readers = self.claimed(runtime)
        with self.lock:
            connections, partials = tuple(self.connections.values()), tuple(self.partials)
        for connection in connections:
            if connection.thread != get_ident() or id(connection) in claimed:
                continue
            for _, error in connection.owner.cleanup():
                runtime.record_error(error)
            if connection.owner.connection is None:
                self.forget(connection)
        for thread, owner in partials:
            if thread == get_ident() and id(owner) not in readers:
                for _, error in owner.cleanup():
                    runtime.record_error(error)
