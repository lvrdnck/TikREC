"""Exact recovery ownership and bounded original exception diagnostics."""

import os

from .lifecycle_lock import _descriptor_identity
from .session_journal_types import JournalError, require


class RecoveryCleanup:
    """Retain partial acquisition owners independently of returned capabilities."""

    def _init_cleanup(self):
        self.extra_owners, self.extra_handles, self.extra_descriptors = [], [], []
        self.descriptor_identities = {}
        self.native_close_guards = []
        self.errors, self.errors_dropped, self.primary = [], 0, None
        self.cleanup_result, self.terminal_result = None, None

    def _error(self, error):
        if self.primary is None:
            self.primary = error
        if any(item is error for item in self.errors):
            return
        if len(self.errors) < 32:
            self.errors.append(error)
        else:
            self.errors_dropped += 1

    def _capture_error(self, error):
        # Register attachments even before generation acknowledgement.
        self._error(error)
        reader = getattr(error, 'manifest_fence_owner', None)
        if reader is not None and not any(held is reader for held in self.readers):
            self.readers.append(reader)
        if reader is not None:
            for _, secondary in reader.errors:
                self._error(secondary)
        for field, target in (('capture_native_owners', self.extra_owners),
                              ('lifecycle_retained_handles', self.extra_handles)):
            for owner in getattr(error, field, ()):
                if not any(held is owner for held in target):
                    target.append(owner)
        for fd in getattr(error, 'lifecycle_retained_descriptors', ()):
            if fd not in self.extra_descriptors:
                self.extra_descriptors.append(fd)
                self.descriptor_identities[fd] = getattr(error, 'lifecycle_descriptor_identities', {}).get(fd)
        if self.extra_handles or self.extra_descriptors:
            self.acquired.add('lease')
        for field in ('capture_cleanup_errors', 'lifecycle_cleanup_errors'):
            for secondary in getattr(error, field, ()):
                self._error(secondary)

    def _expose_errors(self):
        if self.primary is not None:
            self.primary.recovery_owner = self
            self.primary.recovery_errors = tuple(self.errors)
            self.primary.recovery_secondary_errors = tuple(e for e in self.errors if e is not self.primary)
            self.primary.recovery_errors_dropped = self.errors_dropped

    @staticmethod
    def _native_retained(owner):
        return (getattr(owner, 'handle', None) is not None or getattr(owner, 'fd', None) is not None
                or not hasattr(owner, 'handle') and getattr(owner, 'ever_acquired', False))

    def has_retained_ownership(self):
        """Conservatively retain every partial native, lease and SQLite owner."""
        return (any(self._native_retained(o) for o in [*self.objects.values(), *self.extra_owners])
            or self.lease is not None and (not self.lease.closed or not self.lease.handle.closed)
            or any(not getattr(o, 'closed', False) for o in self.extra_handles)
            or bool(self.extra_descriptors)
            or any(guard.retained for guard in self.native_close_guards)
            or any(reader.connection is not None for reader in self.readers))

    def _close_resources(self, *, hooks=True):
        diagnostics, dropped, resources, tried = [], 0, [], set()
        guard_attempts = {id(g): g.attempts for g in self.native_close_guards}
        def diagnostic(error):
            nonlocal dropped
            self._capture_error(error)
            if len(diagnostics) < 32:
                diagnostics.append(repr(error)[:2048])
            else:
                dropped += 1
        def close(held, lease=False):
            if id(held) in tried:
                return
            tried.add(id(held))
            prior = len(held.cleanup_errors) if lease else 0
            try:
                if lease and held.closed:
                    # A lease can mark itself closed before its file close fails.
                    held.handle.close()
                else:
                    held.close()
            except BaseException as error:
                diagnostic(error)
                for secondary in held.cleanup_errors[prior:] if lease else ():
                    if secondary is not error:
                        diagnostic(secondary)
        for original in self.binding['resources']:
            key, acquired = original['key'], original['key'] in self.acquired
            held = self.lease if original['kind'] == 'lease' else self.objects.get(key)
            if acquired and held is not None:
                close(held, original['kind'] == 'lease')
            confirmed = (not acquired or held is not None and
                ((held.closed and held.handle.closed) if original['kind'] == 'lease'
                 else not self._native_retained(held)))
            confirmed = confirmed and not any(g.retained and g.resource_key == key
                                             for g in self.native_close_guards)
            resources.append({'key': key, 'acquired': acquired, 'closed': bool(confirmed)})
            if hooks:
                try:
                    self.fault('after_recovery_cleanup_resource_' + key.replace(':', '_'))
                except BaseException as error:
                    diagnostic(error)
        for held in self.extra_owners:
            close(held)
        for held in self.extra_handles[:]:
            close(held)
            guard = getattr(held, 'guard', None)
            if getattr(held, 'closed', False) and (guard is None or not guard.retained):
                self.extra_handles.remove(held)
        for fd in self.extra_descriptors[:]:
            try:
                expected = self.descriptor_identities[fd]
                guard = next((g for g in self.native_close_guards if g.descriptor == fd), None)
                # A reused descriptor number must never close another object.
                require(guard is not None or expected is not None and _descriptor_identity(fd) == expected,
                        'retained lifecycle descriptor identity is uncertain')
                os.close(fd) if guard is None else guard.close()
                self.extra_descriptors.remove(fd)
                self.descriptor_identities.pop(fd)
            except BaseException as error:
                diagnostic(error)
        for reader in self.readers:
            if reader.connection is not None:
                reader.cleanup()
            for _, error in reader.errors:
                diagnostic(error)
            dropped += reader.errors_dropped
        for guard in self.native_close_guards:
            if guard.attempts == guard_attempts[id(guard)]:
                try:
                    guard.close_retired_reference()
                except BaseException as error:
                    diagnostic(error)
        lease_result = next((item for item in resources if item['key'] == 'lease'), None)
        if self.lease is None and lease_result is not None and lease_result['acquired']:
            lease_result['closed'] = not self.extra_handles and not self.extra_descriptors and not any(
                g.retained and g.resource_key == 'lease' for g in self.native_close_guards)
        retained = self.has_retained_ownership()
        if retained and not diagnostics:
            diagnostic(JournalError('recovery resource ownership remains uncertain'))
        return {'schema_version': 1, 'session_id': self.session_id, 'token': self.token,
            'generation': self.generation, 'authority': self.authority_id,
            'preparation_operation': self.preparation_operation, 'binding_hash': self.binding_hash,
            'proof_operation': self.proof_operation, 'resources': resources,
            'cleanup_complete': all(not r['acquired'] or r['closed'] for r in resources)
                and not retained and not diagnostics and not dropped,
            'diagnostics': diagnostics, 'diagnostics_dropped': dropped}

    def close(self):
        """Try local cleanup once on the caller's SQLite thread, without replay."""
        authority = self.authority
        key = getattr(self, 'registry_key', self.token)
        with authority.recovery_gate:
            with authority.lock:
                require(authority._release_recovery is None, 'recovery execution is still active')
                if authority._recovery_owners.get(key) is not self and not self.has_retained_ownership():
                    return True
                require(authority._recovery_owners.get(key) is self,
                        'this recovery is no longer a registered cleanup owner')
                authority._release_recovery = self
            try:
                self._close_resources(hooks=False)
                self._expose_errors()
                return not self.has_retained_ownership()
            finally:
                with authority.lock:
                    authority._release_recovery = None
                    if not self.has_retained_ownership():
                        authority._recovery_owners.pop(key, None)
