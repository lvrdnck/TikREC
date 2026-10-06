"""Exact reader ownership and bounded teardown for the manifest native fence only."""

from threading import RLock


class ManifestFenceConnection:
    """Keep an unconfirmed close reachable independently of exception tracebacks."""

    def __init__(self, connection):
        self.connection = connection
        self.errors, self.errors_dropped = [], 0
        self.lock = RLock()

    def cleanup(self):
        """Try rollback and close once each; only confirmed close releases this owner."""
        with self.lock:
            if self.connection is None:
                return ()
            errors = []
            for phase in ('rollback', 'close'):
                try:
                    getattr(self.connection, phase)()
                    if phase == 'close':
                        self.connection = None
                except BaseException as error:
                    errors.append((phase, error))
            # Match the attempt/process diagnostic bound without discarding the owner.
            for item in errors:
                if len(self.errors) < 32:
                    self.errors.append(item)
                else:
                    self.errors_dropped += 1
            return tuple(errors)

    def finish(self, primary):
        """Preserve an entry/body exception; successful work plus teardown failure is ambiguous."""
        errors = self.cleanup()
        if errors:
            first = primary if primary is not None else errors[0][1]
            first.manifest_fence_owner = self
            if primary is None:
                raise first

    def evidence(self):
        """Report confirmed cleanup separately from retained reader/diagnostic uncertainty."""
        with self.lock:
            return {'connection_retained': self.connection is not None,
                    'cleanup_complete': self.connection is None,
                    'diagnostic_phases': [phase for phase, _ in self.errors],
                    'diagnostics_dropped': self.errors_dropped}
