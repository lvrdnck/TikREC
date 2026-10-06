"""Recovery-only observational readers with explicit exact SQLite ownership."""

from threading import Event
from uuid import uuid4

from .release_recovery_cleanup import RecoveryCleanup
from .session_journal_manifest_fence import ManifestFenceConnection
from .session_journal_types import require


class RecoveryReads:
    """Reuse journal projections while retaining readers before BEGIN or teardown."""

    def __init__(self, owner):
        self.owner = owner

    def __getattr__(self, name):
        original = getattr(self.owner.journal, name)
        if name in {'operation', 'settlement', 'owned_attempt', 'session', 'release_recovery'}:
            # Projections dispatch their read to this narrowly scoped owner.
            method = getattr(original, '__func__', None)
            if method is not None:
                return method.__get__(self, type(self))
        return original

    def _read(self, action):
        with self.owner.authority.lock:
            require(self.owner.authority._release_recovery is self.owner
                    and self.owner.authority.recovery_gate._is_owned(),
                    'current recovery reader scope required')
        connection, retained, primary, result = None, None, None, None
        try:
            connection = self.owner.journal._connect()
            retained = ManifestFenceConnection(connection)
            self.owner.readers.append(retained)
            connection.execute('BEGIN')
            result = action(connection)
        except BaseException as error:
            primary = error
            hint = getattr(self.owner, 'reconcile_primary', None)
            if hint is not None:
                self.owner._capture_error(hint)
            self.owner._capture_error(error)
        if retained is not None:
            errors = retained.cleanup()
            if errors and getattr(self.owner, 'reconcile_primary', None) is not None:
                self.owner._capture_error(self.owner.reconcile_primary)
            for _, error in errors:
                self.owner._error(error)
            if errors:
                primary = primary or errors[0][1]
                primary.manifest_fence_owner = retained
                if result is not None:
                    self.owner.primary.recovery_read_result = result
        if primary is not None:
            self.owner._expose_errors()
            raise self.owner.primary
        return result


class RecoveryInspection(RecoveryCleanup):
    """Pin initial/history reader uncertainty before any media capability exists."""

    def __init__(self, authority, session_id, token):
        self.authority, self.journal = authority, authority.journal
        self.session_id, self.token = session_id, token
        self.registry_key = 'inspection:' + str(uuid4())
        self.authority_id = self.registry_key
        self._init_cleanup()
        self.objects, self.acquired, self.readers = {}, set(), []
        self.binding, self.lease, self.cancelled = {'resources': []}, None, Event()
        self.generation = self.preparation_operation = self.binding_hash = self.proof_operation = None
        self.fault = lambda _: None
        self.view = RecoveryReads(self)
