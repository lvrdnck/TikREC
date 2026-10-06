"""Explicit, read-only native recovery for an already prepared success release."""

from threading import get_ident
from uuid import uuid4
from dataclasses import asdict
import json

from .lifecycle_lock import acquire_lifecycle
from .release_recovery_native import RecoveryNativeProof
from .session_journal_types import JournalUncertain, digest, encode, require


class ReleaseRecovery:
    """One fresh-generation capability over exact read-only objects and cleanup."""

    def __init__(self, authority, session_id, token, record, fault):
        self.authority, self.journal = authority, authority.journal
        self.session_id, self.token, self.record, self.fault = session_id, token, record, fault
        self.authority_id, self.operation_id = str(uuid4()), lambda: str(uuid4())
        self.binding = record['preparation']['binding']
        self.preparation_operation = record['preparation']['operation']
        self.binding_hash = digest(self.binding)
        self.lease, self.extra_owners = None, []
        self.protection = RecoveryNativeProof(self)
        self.objects, self.acquired = self.protection.objects, self.protection.acquired
        self.readers, self.generation, self.call_thread, self.call_authority = [], None, None, None
        self.proof_operation, self.proof_value = None, None

    def has_retained_ownership(self):
        """Keep the catalog authority reachable while any new resource is uncertain."""
        native = any(getattr(owner, 'handle', None) is not None or getattr(owner, 'fd', None) is not None
                     for owner in self.objects.values())
        lease = self.lease is not None and (not self.lease.closed or not self.lease.handle.closed)
        extras = any((hasattr(owner, 'handle') and owner.handle is not None)
                     or not getattr(owner, 'closed', True) for owner in self.extra_owners)
        readers = any(reader.connection is not None for reader in self.readers)
        return native or lease or extras or readers

    def _authority_evidence(self, settlement):
        owner = self.authority
        cleanup = settlement['cleanup']
        prior_cleanup = None if cleanup is None else {'operation': cleanup['operation'],
            'evidence_hash': digest(cleanup['evidence']),
            'cleanup_complete': cleanup['evidence']['cleanup_complete']}
        return json.loads(encode({'schema_version': 1, 'catalog_id': owner.journal.catalog_id,
            'catalog_native': asdict(owner.catalog.identity), 'catalog_stamp': owner.catalog.initial,
            'state_native': asdict(owner.state.identity), 'state_stamp': owner.state.stamp,
            'owner_lock': {'mode': owner.owner.mode, 'slot': owner.owner.slot,
                'identity': list(owner.owner.identity), 'root': str(owner.owner.root)},
            'media_native': asdict(owner.media.identity),
            'writer_lease': {'mode': self.lease.mode, 'slot': self.lease.slot,
                'identity': list(self.lease.identity), 'root': str(self.lease.root)},
            'preparation_operation': self.preparation_operation, 'binding_hash': self.binding_hash,
            'original_cleanup': prior_cleanup, 'retired': {'catalog_exclusive': True,
                'local_attempt_absent': True, 'original_owner_revoked': True}}))

    def _call(self, kind, method, arguments):
        operation = self.operation_id()
        self.call_thread, self.call_authority = get_ident(), (kind, *arguments)
        before = len(self.readers)
        try:
            try:
                result = method(operation, *arguments, capability=self)
            except JournalUncertain:
                receipt = self.journal.operation(operation)
                require(receipt is not None and receipt['kind'] == kind
                        and receipt['arguments_hash'] == digest(arguments),
                        'recovery operation outcome remains uncertain')
                result = json.loads(receipt['result'])
        finally:
            self.call_thread, self.call_authority = None, None
        for reader in self.readers[before:]:
            require(reader.connection is None and not reader.errors,
                    'recovery journal reader cleanup is uncertain')
        return result

    def _close_resources(self):
        diagnostics, resources = [], []
        for original in self.binding['resources']:
            key = original['key']
            held = self.lease if original['kind'] == 'lease' else self.objects.get(key)
            acquired = key in self.acquired
            confirmed = not acquired
            if acquired:
                try:
                    held.close()
                    confirmed = ((held.closed and held.handle.closed) if original['kind'] == 'lease'
                        else held.handle is None and held.fd is None)
                    require(confirmed, 'recovery close did not confirm: ' + key)
                except BaseException as error:
                    diagnostics.append(repr(error)[:2048])
            resources.append({'key': key, 'acquired': acquired, 'closed': confirmed})
            try:
                self.fault('after_recovery_cleanup_resource_' + key.replace(':', '_'))
            except BaseException as error:
                diagnostics.append(repr(error)[:2048])
        for reader in self.readers:
            diagnostics.extend(repr(error)[:2048] for _, error in reader.errors)
            if reader.connection is not None:
                diagnostics.append('recovery SQLite reader remains open')
        return {'schema_version': 1, 'session_id': self.session_id, 'token': self.token,
            'generation': self.generation, 'authority': self.authority_id,
            'preparation_operation': self.preparation_operation, 'binding_hash': self.binding_hash,
            'proof_operation': self.proof_operation, 'resources': resources,
            'cleanup_complete': all(not item['acquired'] or item['closed'] for item in resources)
                and not diagnostics,
            'diagnostics': diagnostics[:32], 'diagnostics_dropped': max(0, len(diagnostics) - 32)}

    def _clean_readers(self):
        require(all(reader.connection is None for reader in self.readers),
                'recovery transaction owner remains open')

    def run(self, settlement):
        """Prove and release only this prepared attempt; every phase has a crash boundary."""
        primary = None
        try:
            self.authority.assert_recovery_retired(self.token)
            self.lease = acquire_lifecycle(self.authority.root, 'writer', existing_only=True)
            self.acquired.add('lease')
            result = self._call('begin_release_recovery', self.journal.begin_release_recovery,
                [self.token, self.session_id, self.authority_id, self._authority_evidence(settlement)])
            self.generation = result['generation']
            self.authority._release_recovery = self
            self.fault('after_recovery_authority')
            self.protection.open_all()
            proof = self.protection.verify()
            proof_result = self._call('record_release_recovery_proof',
                self.journal.record_release_recovery_proof,
                [self.token, self.generation, self.authority_id, proof])
            self.proof_operation, self.proof_value = proof_result['operation'], proof
            self.fault('after_recovery_proof')
            require(self.protection.verify() == proof, 'recovery proof drifted before cleanup')
        except BaseException as error:
            primary = error
        if self.generation is not None:
            try:
                cleanup = self._close_resources()
                self._clean_readers()
                self.fault('after_recovery_cleanup')
                cleanup_result = self._call('record_release_recovery_cleanup',
                    self.journal.record_release_recovery_cleanup,
                    [self.token, self.generation, self.authority_id, cleanup])
                self.fault('after_recovery_cleanup_record')
                require(cleanup_result['evidence'] == cleanup, 'recovery cleanup receipt conflicts')
            except BaseException as error:
                if primary is None:
                    primary = error
                else:
                    primary.add_note('recovery cleanup or receipt also failed')
        elif self.lease is not None:
            try:
                self.lease.close()
            except BaseException as error:
                if primary is None:
                    primary = error
                else:
                    primary.add_note('recovery root lease cleanup also failed')
        if primary is not None:
            raise primary
        require(cleanup['cleanup_complete'] and self.proof_operation is not None,
                'recovery proof or cleanup remains uncertain')
        evidence = {'preparation_operation': self.preparation_operation,
            'binding_hash': self.binding_hash, 'generation': self.generation,
            'authority': self.authority_id,
            'authority_operation': self.journal.release_recovery(self.token)['head']['authority_operation'],
            'proof_operation': self.proof_operation, 'proof_hash': digest(self.proof_value),
            'cleanup_operation': cleanup_result['operation'], 'cleanup_hash': digest(cleanup),
            'cleanup_complete': True, 'returned_units': 1}
        self._clean_readers()
        self.fault('before_recovery_terminal')
        terminal = self._call('settle_release_recovery', self.journal.settle_release_recovery,
            [self.token, self.generation, self.authority_id, evidence])
        self.fault('after_recovery_terminal')
        return terminal


def recover_prepared_release(authority, session_id, token, *, fault=lambda _: None):
    """Return history idempotently or explicitly recover one prepared success."""
    from .session_journal_types import identifier
    identifier(session_id)
    identifier(token)
    authority.assert_held()
    record = authority.journal.settlement(token)
    require(record is not None and record['preparation'] is not None,
            'recovery is unsupported before successful release preparation')
    binding = record['preparation']['binding']
    require(binding['session_id'] == session_id and binding['token'] == token,
            'recovery session or attempt address conflicts')
    if record['state'] == 'released':
        return record
    require(record['state'] in {'cleanup_pending', 'cleanup_incomplete', 'cleanup_confirmed'},
            'prepared success is not eligible for recovery')
    authority.assert_recovery_retired(token)
    recovery = ReleaseRecovery(authority, session_id, token, record, fault)
    authority._release_recovery = recovery
    authority._recovery_owners[token] = recovery
    try:
        result = recovery.run(record)
        return authority.journal.settlement(token) or result
    finally:
        authority._release_recovery = None
        if not recovery.has_retained_ownership():
            authority._recovery_owners.pop(token, None)
