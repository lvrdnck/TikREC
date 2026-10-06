"""Explicit, read-only native recovery for an already prepared success release."""

from threading import Event, get_ident
from uuid import uuid4
from dataclasses import asdict
import json

from .lifecycle_lock import acquire_lifecycle
from .release_recovery_native import RecoveryNativeProof
from .release_recovery_cleanup import RecoveryCleanup
from .release_recovery_handles import cleanup_scope
from .release_recovery_reads import RecoveryInspection, RecoveryReads
from .session_journal_types import JournalUncertain, digest, encode, require


class ReleaseRecovery(RecoveryCleanup):
    """One fresh-generation capability over exact read-only objects and cleanup."""

    def __init__(self, authority, session_id, token, record, fault):
        self.authority, self.journal = authority, authority.journal
        self.session_id, self.token, self.record, self.fault = session_id, token, record, fault
        self.authority_id, self.operation_id = str(uuid4()), lambda: str(uuid4())
        self.binding = record['preparation']['binding']
        self.preparation_operation = record['preparation']['operation']
        self.binding_hash = digest(self.binding)
        self._init_cleanup()
        self.lease, self.cancelled = None, Event()
        self.protection = RecoveryNativeProof(self)
        self.objects, self.acquired = self.protection.objects, self.protection.acquired
        self.readers, self.generation, self.call_thread, self.call_authority = [], None, None, None
        self.view = RecoveryReads(self)
        self.proof_operation, self.proof_value = None, None
        self.execution_thread = None
        self.terminal_started = False

    def _check_cancelled(self):
        require(not self.cancelled.is_set(), 'explicit release recovery cancelled')

    def _accepted(self, kind, result):
        # Keep acknowledged committed facts even if the exact reader teardown failed.
        if kind == 'begin_release_recovery':
            self.generation = result['generation']
        elif kind == 'record_release_recovery_proof':
            self.proof_operation, self.proof_value = result['operation'], result['evidence']
        elif kind == 'record_release_recovery_cleanup':
            self.cleanup_result = result['evidence']
        elif kind == 'settle_release_recovery':
            self.terminal_result = result

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
        # Bind the decision briefly; SQL waits, reconciliation and teardown use
        # the execution fence and durable transactions outside capture admission.
        with self.authority.lock:
            require(self.execution_thread == get_ident(), 'recovery execution thread conflicts')
            if kind != 'record_release_recovery_cleanup':
                self._check_cancelled()
            if kind == 'settle_release_recovery':
                self.terminal_started = True
            self.call_thread, self.call_authority = get_ident(), (kind, *arguments)
        before, uncertain = len(self.readers), None
        try:
            try:
                result = method(operation, *arguments, capability=self)
            except JournalUncertain as error:
                uncertain = error
                self.reconcile_primary = error.__cause__ or error
                try:
                    receipt = self.view.operation(operation)
                    require(receipt is not None and receipt['kind'] == kind
                            and receipt['arguments_hash'] == digest(arguments),
                            'recovery operation outcome remains uncertain')
                    result = json.loads(receipt['result'])
                except BaseException as secondary:
                    self._capture_error(error.__cause__ or error)
                    self._error(secondary)
                    observed = getattr(secondary, 'recovery_read_result', None)
                    if (observed is not None and observed['kind'] == kind
                            and observed['arguments_hash'] == digest(arguments)):
                        self._accepted(kind, json.loads(observed['result']))
                    raise self.primary
                finally:
                    self.reconcile_primary = None
            self._accepted(kind, result)
            failed = [error for reader in self.readers[before:] for _, error in reader.errors]
            if failed:
                first = (uncertain.__cause__ or uncertain) if uncertain is not None else failed[0]
                self._capture_error(first or failed[0])
                for error in failed:
                    self._error(error)
                raise self.primary
            require(all(r.connection is None for r in self.readers[before:]),
                    'recovery transaction ownership remains uncertain')
            return result
        except BaseException as error:
            self._capture_error(error)
            for reader in self.readers[before:]:
                for _, secondary in reader.errors:
                    self._error(secondary)
                self.errors_dropped += reader.errors_dropped
            raise self.primary
        finally:
            with self.authority.lock:
                self.call_thread, self.call_authority = None, None

    def _clean_readers(self):
        require(all(reader.connection is None for reader in self.readers),
                'recovery transaction owner remains open')

    def run(self, settlement):
        """Prove and release only this prepared attempt; every phase has a crash boundary."""
        require(self.execution_thread is None, 'recovery execution is single-use')
        self.execution_thread = get_ident()
        try:
            self._check_cancelled()
            with cleanup_scope(self):
                self.lease = acquire_lifecycle(self.authority.root, 'writer', existing_only=True)
            self.acquired.add('lease')
            result = self._call('begin_release_recovery', self.journal.begin_release_recovery,
                [self.token, self.session_id, self.authority_id, self._authority_evidence(settlement)])
            self.generation = result['generation']
            self.fault('after_recovery_authority')
            self.protection.open_all()
            proof = self.protection.verify()
            proof_result = self._call('record_release_recovery_proof',
                self.journal.record_release_recovery_proof,
                [self.token, self.generation, self.authority_id, proof])
            self.proof_operation, self.proof_value = proof_result['operation'], proof
            self.fault('after_recovery_proof')
            require(self.protection.same_proof(self.protection.verify(), proof),
                    'recovery proof drifted before cleanup')
        except BaseException as error:
            self._capture_error(error)
        # Independent safe cleanup also runs before a generation acknowledgement.
        cleanup = self._close_resources()
        if self.generation is not None:
            try:
                self._clean_readers()
                self.fault('after_recovery_cleanup')
                cleanup_result = self._call('record_release_recovery_cleanup',
                    self.journal.record_release_recovery_cleanup,
                    [self.token, self.generation, self.authority_id, cleanup])
                self.fault('after_recovery_cleanup_record')
                require(cleanup_result['evidence'] == cleanup, 'recovery cleanup receipt conflicts')
            except BaseException as error:
                self._capture_error(error)
        if self.primary is not None:
            self._expose_errors()
            raise self.primary
        require(cleanup['cleanup_complete'] and self.proof_operation is not None,
                'recovery proof or cleanup remains uncertain')
        evidence = {'preparation_operation': self.preparation_operation,
            'binding_hash': self.binding_hash, 'generation': self.generation,
            'authority': self.authority_id,
            'authority_operation': self.view.release_recovery(self.token)['head']['authority_operation'],
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
    require(authority.recovery_gate._is_owned(), 'current recovery execution fence required')
    with authority.lock:
        authority.assert_held()
        require(authority._release_recovery is None, 'another recovery execution is active')
        # At most one uncertain initial/history reader scope may remain outstanding.
        require(not any(isinstance(owner, RecoveryInspection) and owner.has_retained_ownership()
                        for owner in authority._recovery_owners.values()),
                'a prior recovery inspection still owns journal resources')
        inspection = RecoveryInspection(authority, session_id, token)
        authority._recovery_owners[inspection.registry_key] = inspection
        authority._release_recovery = inspection
    recovery = inspection
    try:
        # Catalog protection covers these observational reads as well as mutations.
        record = inspection.view.settlement(token)
        require(record is not None and record['preparation'] is not None,
                'recovery is unsupported before successful release preparation')
        binding = record['preparation']['binding']
        require(binding['session_id'] == session_id and binding['token'] == token,
                'recovery session or attempt address conflicts')
        if record['state'] == 'released':
            return record
        require(record['state'] in {'cleanup_pending', 'cleanup_incomplete', 'cleanup_confirmed'},
                'prepared success is not eligible for recovery')
        with authority.lock:
            authority.assert_recovery_retired(token)
            recovery = ReleaseRecovery(authority, session_id, token, record, fault)
            recovery.cancelled = inspection.cancelled
            authority._release_recovery = recovery
            authority._recovery_owners[token] = recovery
        result = recovery.run(record)
        return recovery.view.settlement(token) or result
    except BaseException as error:
        recovery._capture_error(error)
        recovery._expose_errors()
        raise recovery.primary
    finally:
        with authority.lock:
            authority._release_recovery = None
            if not recovery.has_retained_ownership():
                authority._recovery_owners.pop(getattr(recovery, 'registry_key', token), None)
            if not inspection.has_retained_ownership():
                authority._recovery_owners.pop(inspection.registry_key, None)
