"""Explicit single native scheduler authority for the isolated capture bridge."""

import json
from contextlib import ExitStack
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

    def __init__(self, journal, root):
        self.journal, self.root = journal, Path(root).absolute()
        self.lock, self.bridges, self.pending = RLock(), {}, set()
        self._stack, self.leases = ExitStack(), []
        try:
            require(self.root != journal.path.parent, "state and media scopes must be separate")
            self.owner = self._stack.enter_context(acquire_lifecycle(journal.path.parent, "retention"))
            self.state = self._stack.enter_context(NativeHandle(journal.path.parent, directory=True))
            self.catalog = self._stack.enter_context(NativeHandle(journal.path, shared=True))
            self.media = self._stack.enter_context(NativeHandle(self.root, directory=True))
            # The shared native DB handle denies replacement while permitting SQLite I/O.
            self.journal.status()
        except BaseException as original:
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

    def close(self):
        """Release process handles while durable capture/task/evidence ownership persists."""
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
