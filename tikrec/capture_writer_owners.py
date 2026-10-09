"""Bounded, original-thread native lifetime proof for capture part/control writers."""

import os
from contextlib import contextmanager
from contextvars import ContextVar
from threading import get_ident

from .release_recovery_handles import NativeCloseGuard
from .session_journal_types import require

_current = ContextVar('capture_writer_owner', default=None)


def open_capture_file(path, mode, **options):
    """Use the current capture's original-owner ledger, or ordinary file semantics."""
    owner = _current.get()
    return path.open(mode, **options) if owner is None else owner.open(path, mode, **options)


@contextmanager
def writer_scope(owner):
    """Bind only synchronous capture execution; context reset cannot transfer ownership."""
    if owner is None:
        yield
        return
    require(not owner.entered and _current.get() is None, 'capture writer scope is single-use')
    owner.entered, owner.thread = True, get_ident()
    token = _current.set(owner)
    try:
        yield
    finally:
        _current.reset(token)
        owner.exited = True


class CaptureWriterOwners:
    """Retain uncertain original streams; discard confirmed closures without unbounded growth."""

    def __init__(self, session_id, generation):
        self.session_id, self.generation = session_id, generation
        self.native_close_guards, self.streams, self.errors = [], [], []
        self.entered = self.exited = self.acquisition_uncertain = False
        self.thread = None
        self.opened = self.closed = self.parts_opened = 0

    def _error(self, error):
        for diagnostic in (error, *getattr(error, 'capture_cleanup_errors', ())):
            if any(diagnostic is previous for previous in self.errors):
                continue
            if len(self.errors) < 32:
                self.errors.append(diagnostic)
            else:
                # An unrecorded acquisition/close fault cannot support a retirement proof.
                self.acquisition_uncertain = True

    def open(self, path, mode, **options):
        """Register the original stream before native duplication or the first header write."""
        require(self.entered and not self.exited and self.thread == get_ident(),
                'capture writer scope is not current')
        try:
            raw = path.open(mode, **options)
        except BaseException as error:
            self.acquisition_uncertain = True
            self._error(error)
            raise
        entry = {'raw': raw, 'guard': None}
        self.streams.append(entry)
        self.opened += 1
        part = mode == 'xb'
        self.parts_opened += int(part)
        if os.name != 'nt':
            return raw
        import msvcrt
        try:
            entry['guard'] = NativeCloseGuard(self, msvcrt.get_osfhandle(raw.fileno()),
                raw.fileno(), resource_key='capture_part' if part else 'capture_control')
        except BaseException as error:
            self._error(error)
            raise
        return _WriterStream(self, entry)

    def _confirmed(self, entry):
        guard, raw = entry['guard'], entry['raw']
        if guard is not None and not guard.retained and raw.closed:
            self.streams.remove(entry)
            self.native_close_guards.remove(guard)
            self.closed += 1

    def retire(self):
        """Retry exact guarded references only after the caller proves capture quiescence."""
        require(self.entered and self.exited, 'capture writer execution is not retired')
        for entry in tuple(self.streams):
            raw, guard = entry['raw'], entry['guard']
            if guard is None:
                continue
            try:
                guard.close_retired_reference()
                if guard.retained:
                    guard.close(None if raw.closed else raw.close)
            except BaseException as error:
                self._error(error)
            self._confirmed(entry)
        return self.retired()

    def retired(self):
        """Require completed original execution and native proof for every acquisition."""
        return (self.entered and self.exited and not self.acquisition_uncertain
                and self.closed == self.opened and not self.streams
                and not self.native_close_guards)

    def known_cleanup(self, errors):
        """Allow only identified writer-close diagnostics, never unknown source/callback faults."""
        return all(any(error is recorded for recorded in self.errors) for error in errors)


class _WriterStream:
    def __init__(self, owner, entry):
        self.owner, self.entry = owner, entry

    def __getattr__(self, name):
        return getattr(self.entry['raw'], name)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        """Preserve close failures and confirm native retirement before dropping bookkeeping."""
        if self.entry not in self.owner.streams:
            return
        raw, guard = self.entry['raw'], self.entry['guard']
        try:
            guard.close(None if raw.closed else raw.close)
        except BaseException as error:
            self.owner._error(error)
            raise
        finally:
            self.owner._confirmed(self.entry)
