"""Explicit single native scheduler authority for the isolated capture bridge."""

import json
from contextlib import ExitStack, nullcontext
from pathlib import Path
from threading import RLock
from uuid import uuid4

from .capture_handoff_marker import inspect_pending
from .capture_handoff_native import NativeHandle, child_identity
from .lifecycle_lock import acquire_lifecycle
from .session_journal_types import JournalConflict, JournalUncertain, SessionIntent, require


def operation_id():
    """Allocate a permanent operation identity before any potentially ambiguous commit."""
    return str(uuid4())


class CaptureAuthority:
    """Hold the known catalog owner lock and native namespace across all bridge work.

    Callers supply an existing identified journal and explicit local media root.
    No service import, default location, initialization, migration or discovery is
    performed. Sources/writers must run through this single trusted authority.
    """

    def __init__(self, journal, root, *, cleanup_guards=False):
        self.journal, self.root = journal, Path(root).absolute()
        self.lock, self.bridges, self.pending = RLock(), {}, set()
        self.recovery_gate = RLock()
        self._attempts, self._recovery_owners, self._release_recovery = {}, {}, None
        self._stack, self.leases = ExitStack(), []
        self.native_close_guards = []
        self.cleanup_guards = cleanup_guards
        # The opt-in launcher retains exact startup owners; legacy callers stay unchanged.
        from .release_recovery_handles import cleanup_scope, NativeCloseGuard
        factory = (lambda h: NativeCloseGuard(self, h, resource_key='authority_native')) if cleanup_guards else None
        try:
            require(self.root != journal.path.parent, "state and media scopes must be separate")
            with cleanup_scope(self) if cleanup_guards else nullcontext():
                self.owner = self._stack.enter_context(acquire_lifecycle(journal.path.parent, "retention"))
            self.state = self._stack.enter_context(NativeHandle(journal.path.parent, directory=True, cleanup_guard_factory=factory))
            self.catalog = self._stack.enter_context(NativeHandle(journal.path, shared=True, cleanup_guard_factory=factory))
            self.media = self._stack.enter_context(NativeHandle(self.root, directory=True, cleanup_guard_factory=factory))
            # The shared native DB handle denies replacement while permitting SQLite I/O.
            self.journal.status()
        except BaseException as original:
            if cleanup_guards:
                original.capture_authority_owner = self
            try:
                self._stack.close()
            except BaseException as cleanup:
                original.capture_cleanup_errors = [cleanup]
                raise original from cleanup
            raise

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        try:
            self.close()
        except BaseException as cleanup:
            if len(_exc) > 1 and _exc[1] is not None:
                _exc[1].add_note("native authority teardown also failed")
                _exc[1].capture_cleanup_errors = [cleanup]
            else:
                raise

    def assert_held(self):
        """Recheck the exact catalog/root owner before opening or committing work."""
        self.owner.assert_held()
        for held in (self.state, self.catalog, self.media):
            held.verify()

    def invoke(self, method, operation, *args, **kwargs):
        """Reconcile a lost acknowledgement by the same durable operation identity."""
        try:
            return method(operation, *args, **kwargs)
        except JournalUncertain:
            self.journal.status()
            receipt = self.journal.operation(operation)
            if receipt is None:
                raise
            require(receipt["kind"] == method.__name__, "operation reconciliation kind conflicts")
            return json.loads(receipt["result"])

    def reserve(self, output, creator, expected_room, *, raw_copy=False, started_at,
                automatic_claim=None, slot=None):
        """Reserve native disjoint claims/unit before any source or writer is started."""
        output = Path(output).absolute()
        require(output.parent == self.root and output.suffix.casefold() == ".mp4",
                "bridge output must be an immediate MP4 in the explicit root")
        from .release_recovery_handles import cleanup_scope
        with cleanup_scope(self) if self.cleanup_guards else nullcontext():
            lease = acquire_lifecycle(self.root, "writer")
        self.leases.append(lease)
        with self.lock:
            try:
                self.assert_held()
                require(not self.pending, "unreconciled handoff prevents new admission")
                intent = SessionIntent(operation_id(), creator, expected_room, str(output),
                                       str(output.with_suffix(".parts")), self.media.identity,
                                       child_identity(self.media, output.name),
                                       child_identity(self.media, output.with_suffix(".parts").name),
                                       raw_copy, started_at, automatic_claim)
                if output.exists() or Path(intent.parts_path).exists():
                    raise JournalConflict("requested artifact path already exists")
                # Missing targets use a pinned parent key; journal claims still guard reservations.
                accepted = self.invoke(self.journal.reserve, operation_id(), intent, slot=slot)
                row = self.journal.session(intent.session_id)
                require(row["phase"] == "reserved" and row["revision"] == accepted["revision"],
                        "acceptance receipt is not fresh capture authority")
                from .capture_handoff import CaptureBridge
                bridge = CaptureBridge(self, intent, accepted, lease)
                self.bridges[intent.session_id] = bridge
                return bridge
            except BaseException as original:
                # If acceptance is uncertain, no writer starts and its durable binding remains.
                try:
                    lease.close()
                except BaseException as cleanup:
                    original.capture_cleanup_errors = [cleanup]
                    raise original from cleanup
                raise

    def inspect(self, session_id):
        """Reconcile queued versus still-held state, never reconstruct writer permission."""
        with self.lock:
            result = inspect_pending(self, session_id)
            self.pending.discard(session_id)
            return result

    def recover_prepared_release(self, session_id, token, *, fault=lambda _: None):
        """Explicitly recover one prepared successful release after a restart."""
        from .release_recovery import recover_prepared_release
        # Competing recovery executions serialize without blocking capture admission.
        with self.recovery_gate:
            return recover_prepared_release(self, session_id, token, fault=fault)

    def cancel_release_recovery(self, session_id, token):
        """Request addressed cooperative cancellation without waiting for file hashing."""
        with self.lock:
            recovery = self._release_recovery
            if recovery is None:
                return False
            require(recovery.session_id == session_id and recovery.token == token,
                    'cancellation address does not match active recovery')
            if getattr(recovery, 'terminal_started', False):
                # Once terminal accounting starts, later cancellation cannot undo it.
                return False
            recovery.cancelled.set()
            return True

    def assert_recovery_retired(self, token):
        """Prove no same-process original capability still owns this prepared attempt."""
        runner = self._attempts.get(token)
        if runner is not None:
            require(runner.closed and runner.settlement_owner is not None,
                    'original live attempt owner still exists')
            require(all(reader.connection is None and not reader.errors
                        for reader in runner.settlement_owner.readers),
                    'original settlement reader ownership is unresolved')
            for key, held in runner.settlement_owner.objects:
                require((held.closed and held.handle.closed) if key == 'lease' else
                        held.handle is None and getattr(held, 'fd', None) is None,
                        'original native release owners are still live')
        require(not any(recovery.has_retained_ownership() for recovery in self._recovery_owners.values()),
                'a prior recovery still owns native or journal resources')
        self.assert_held()
        return True

    def close(self):
        """Release process handles while durable capture/task/evidence ownership persists."""
        with self.lock:
            require(self._release_recovery is None, 'active recovery protects catalog lifetime')
            require(not any(owner.has_retained_ownership() for owner in self._recovery_owners.values()),
                    'recovery native owners must remain reachable until confirmed cleanup')
            errors = []
            for lease in self.leases:
                try:
                    lease.close()
                except BaseException as error:
                    errors.append(error)
            try:
                self._stack.close()
            except BaseException as error:
                errors.append(error)
            if errors:
                raise errors[0]
