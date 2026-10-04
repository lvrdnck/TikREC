"""Explicit committed capture seal -> held readers; no queue claim or launch."""

import os
from pathlib import Path
from threading import RLock

from .capture_handoff_marker import MARKER_NAME
from .lifecycle_lock import LOCK_NAME, acquire_lifecycle
from .sealed_input_native import ReadProtection
from .sealed_input_validation import (SealedInputEvidence, inventory_names, target_binding,
                                      verify_inventory)
from .session_journal_types import identifier, require, sha256


class SealedInputError(RuntimeError):
    """First failure plus secondary cleanup evidence and a reachable native owner."""

    def __init__(self, guard, original):
        super().__init__("sealed input proof failed; preserve evidence and retained owners")
        self.guard, self.original = guard, original
        self.diagnostics = tuple(guard.cleanup_errors)


class SealedInputs:
    """Lease-scoped read protection, not durable launch authorization.

    A future caller must hold this guard until every reader's whole-job exit is
    proved and final revalidation succeeds. Close is an explicit lifetime decision;
    this primitive neither owns reader children nor guesses their exit.
    """

    def __init__(self, authority, session_id, revision, seal_hash, fault):
        self.authority, self.session_id = authority, session_id
        self.revision, self.seal_hash, self._fault = revision, seal_hash, fault
        self.handles, self.lifecycle, self.cleanup_errors = [], None, []
        self.extra_handles, self.extra_descriptors = [], []
        self.closed, self.acquired, self._snapshot = False, False, None
        self._lock = RLock()

    @property
    def retained(self):
        """Return possibly live owners, including those retained after failed cleanup."""
        owners = [held for held in self.handles if held.handle is not None]
        if self.lifecycle is not None and not self.lifecycle.handle.closed:
            owners.append(self.lifecycle)
        return tuple(owners + self.extra_handles + self.extra_descriptors)

    def _open(self, path, **options):
        held = ReadProtection(path, **options)
        # Ownership exists before native allocation/validation can throw.
        self.handles.append(held)
        return held.open()

    def _target(self):
        with self.authority.lock:
            self.authority.assert_held()
            row = self.authority.journal.sealed_input(self.session_id)
            intent, seal = target_binding(row, self.session_id, self.revision, self.seal_hash)
            require(intent.root == self.authority.media.identity, "sealed root/catalog conflicts")
            return row, intent, seal

    def _acquire(self):
        identifier(self.session_id)
        require(type(self.revision) is int and self.revision > 0, "invalid expected revision")
        sha256(self.seal_hash)
        # Establish compatible root protection BEFORE taking the authority lock.
        root = self._open(self.authority.root, directory=True)
        lock = self._open(root.path / LOCK_NAME, namespace=True)
        require(lock.size == 64, "missing or malformed existing lifecycle lock")
        self.lifecycle = acquire_lifecycle(root.path, "writer", cleanup_errors=self.cleanup_errors)
        self._fault("after_lifecycle")
        self._snapshot, self.intent, self.seal = self._target()
        require(root.identity == self.intent.root, "sealed root identity changed")
        self.directory = self._open(Path(self.intent.parts_path), directory=True)
        self._fault("before_inventory")
        inventory_names(self.directory.path, self.seal)
        self.files = []
        for number, artifact in enumerate(self.seal.artifacts, 1):
            held = self._open(self.directory.path / artifact.identity.components[-1])
            self.files.append(held)
            self._fault("after_open_" + str(number))
        self.marker = self._open(self.directory.path / MARKER_NAME)
        self._marker_hash = self._verify()
        self._fault("after_inventory")
        # Filesystem work above holds neither SQLite transaction nor authority lock.
        require(self._target()[0] == self._snapshot, "sealed target changed during acquisition")
        self.acquired = True

    def _verify(self):
        self.lifecycle.assert_held()
        for held in self.handles[:2]:
            held.verify()
        return verify_inventory(self.authority, self._snapshot, self.intent, self.seal,
                                self.directory, self.files, self.marker)

    def revalidate(self):
        """Recheck target before/after held evidence; return immutable lease-scoped proof."""
        with self._lock:
            require(self.acquired and not self.closed, "sealed input guard is closed or unacquired")
            require(self._target()[0] == self._snapshot, "sealed target is stale")
            marker_hash = self._verify()
            require(marker_hash == self._marker_hash, "held pending marker bytes changed")
            require(self._target()[0] == self._snapshot, "sealed target changed during revalidation")
            return SealedInputEvidence(self.session_id, self.revision, self.seal_hash,
                self.intent, self.seal, tuple(held.path for artifact, held in
                    zip(self.seal.artifacts, self.files, strict=True) if artifact.role == "flv"), marker_hash)

    def close(self):
        """Attempt every exact release; retained owners and diagnostics survive failure."""
        with self._lock:
            self.acquired = False
            errors = []
            for held in reversed(self.handles):
                try:
                    held.close()
                except BaseException as error:
                    errors.append(error)
            if self.lifecycle is not None:
                try:
                    self.lifecycle.close()
                    # Lifecycle close may previously have marked itself closed while
                    # a file close failed. Retry only that retained exact file owner.
                    if not self.lifecycle.handle.closed:
                        self.lifecycle.handle.close()
                except BaseException as error:
                    errors.append(error)
            for handle in self.extra_handles[:]:
                try:
                    handle.close()
                    self.extra_handles.remove(handle)
                except BaseException as error:
                    errors.append(error)
            for descriptor in self.extra_descriptors[:]:
                try:
                    os.close(descriptor)
                    self.extra_descriptors.remove(descriptor)
                except BaseException as error:
                    errors.append(error)
            self.closed = not self.retained
            self.cleanup_errors.extend(errors)
            if errors:
                raise SealedInputError(self, errors[0]) from errors[0]

    def __enter__(self):
        require(self.acquired and not self.closed, "sealed input guard is closed")
        return self

    def __exit__(self, _type, original, _trace):
        try:
            self.close()
        except SealedInputError as cleanup:
            if original is None:
                raise
            original.sealed_input_guard = self
            original.sealed_input_cleanup = cleanup.diagnostics
            original.add_note("sealed input teardown also failed; retained guard is attached")


def acquire_sealed_inputs(authority, session_id, *, expected_revision, expected_seal_hash,
                          fault=lambda _: None):
    """Acquire one explicit original H seal without discovery, repair or task mutation."""
    guard = SealedInputs(authority, session_id, expected_revision, expected_seal_hash, fault)
    try:
        guard._acquire()
        return guard
    except BaseException as original:
        guard.extra_handles.extend(getattr(original, "lifecycle_retained_handles", ()))
        guard.extra_descriptors.extend(getattr(original, "lifecycle_retained_descriptors", ()))
        try:
            guard.close()
        except BaseException:
            # close recorded secondary failures; the acquisition failure stays first.
            pass
        raise SealedInputError(guard, original) from original
