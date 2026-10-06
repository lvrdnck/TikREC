"""Unreconstructible success capability over original continuously held manifest owners."""

import json
from threading import get_ident

from .session_journal_types import digest, encode, require
from .settlement_resources import resources, children_complete, check_children, cleanup
from .session_journal_settlement_checks import child_facts


class OwnedSettlement:
    """Only cleanup/accounting may continue after immutable preparation revokes execution."""

    def __init__(self, manifest):
        runner = manifest.coordinator
        require(getattr(runner, 'settlement_capable', False) and runner.manifest_adapter is manifest
                and manifest.used and manifest.error is None and manifest.capability is not None
                and runner.manifest_owner is manifest.capability and manifest.capability.installed
                and getattr(runner, 'settlement_owner', None) is None, 'original successful live manifest required')
        self.manifest, self.runner = manifest, runner
        runner.settlement_owner = self
        self.operation, self.binding, self.objects = None, None, ()
        self.readers, self.used = [], False
        self.cleanup_result, self.first_cleanup_error, self.terminal_result = None, None, None
        self.state = 'live_completion'
        self.call_authority, self.call_thread = None, None

    def _proof(self):
        runner, cap = self.runner, self.manifest.capability
        require(runner.settlement_owner is self and runner.manifest_adapter is self.manifest and self.manifest.error is None
                and self.manifest.coordinator is runner and runner.manifest_owner is cap
                and cap.installed and cap.preserved and cap.written
                and (cap.fence_owner is None or cap.fence_owner.connection is None and not cap.fence_owner.errors),
                'completion or reader ownership ambiguous')
        cap.revalidate()
        children_complete(runner)
        owner = runner.journal.owned_attempt(runner.token)
        require(owner['state'] == 'held' and owner['revision'] == runner.revision, 'success ownership revoked')
        record = runner.journal.manifest_completion(runner.token)
        require(record is not None and record['operation'] == cap.operation and record['binding'] == cap.binding
                and len(record['steps']) == 3 and record['steps'][-1]['phase'] == 'installed'
                and record['steps'][-1]['evidence']['required_flushed'], 'fresh installed receipt missing')
        objects, scope = resources(runner)
        children = runner.journal._read(lambda db: child_facts(db, runner.token))
        check_children(runner, children)
        binding = {k: owner[k] for k in ('session_id', 'token', 'owner', 'h_operation',
            'h_revision', 'seal_hash', 'marker_hash')}
        binding.update(manifest=record, publication=runner.journal.publication(runner.token),
                       children=children, resources=scope,
                       claims={'unit': {'session': owner['session_id'], 'kind': 'task'},
                           'artifacts': self.manifest.coordinator.guard._snapshot['artifacts'],
                           'rooms': self.manifest.coordinator.guard._snapshot['rooms'],
                           'task_revision': runner.claimed['task_revision'], 'attempt': owner['attempt']})
        cap.revalidate()
        return objects, json.loads(encode(binding))

    def _pending_proof(self):
        """Recheck held objects after revocation solely to authorize their prepared release."""
        runner, cap = self.runner, self.manifest.capability
        require(runner.settlement_owner is self and runner.manifest_owner is cap
                and cap.predecessor.handle == cap.original_handle and cap.parent.handle == cap.parent_handle
                and cap.stage is cap.stage_owner and cap.stage.handle == cap.stage_handle
                and cap.stage.fd == cap.stage_fd, 'prepared control owner replaced')
        self._readers_clean()
        runner.authority.assert_held()
        runner.guard.lifecycle.assert_held()
        for held in runner.guard.handles[:2]:
            held.verify()
        cap.check_inputs()
        publication = cap.publication.capability
        require(publication.held.handle == publication.original_handle
                and publication.held.fd == publication.original_fd, 'prepared output owner replaced')
        runner.scratch.workspace.verify()
        publication.check_scratch()
        require(runner.scratch._hash(publication.held) == self.binding['publication']['evidence']['sha256'],
                'prepared output bytes changed')
        cap.check_inputs()
        publication.check_scratch()
        objects, scope = resources(runner)
        require(all(a is b and ka == kb for (ka, a), (kb, b) in zip(self.objects, objects, strict=True)),
                'prepared cleanup objects replaced')
        for expected, actual, (_, held) in zip(self.binding['resources'], scope, objects, strict=True):
            if expected['kind'] == 'native' and held.directory:
                require(expected['evidence']['identity'] == actual['evidence']['identity']
                        and expected['evidence']['stamp'].split(':')[:2] == actual['evidence']['stamp'].split(':')[:2],
                        'prepared namespace identity changed')
            else:
                require(expected == actual, 'prepared native evidence changed')
        check_children(runner, self.binding['children'])
        record = runner.journal.settlement(runner.token)
        require(record['state'] == 'cleanup_pending' and record['preparation']['operation'] == self.operation
                and record['preparation']['binding'] == self.binding, 'prepared release receipt changed')

    def _call(self, kind, method, value, *, preparing=False):
        runner = self.runner
        with runner.transition_lock:
            with runner.gate:
                if preparing:
                    require(not runner.cancelled.is_set() and not runner.closed, 'settlement preparation cancelled')
                args = [runner.token, runner.owner, runner.revision, value]
                before = len(self.readers)
                self.call_authority, self.call_thread = (kind, *args), get_ident()
                try:
                    result = runner._call(kind, lambda operation, *tail: method(operation, *tail, capability=self), args)
                finally:
                    self.call_authority, self.call_thread = None, None
                    for reader in self.readers[before:]:
                        for _, error in reader.errors:
                            runner._error(error)
                    # Even lost preparation acknowledgement freezes local execution.
                    runner.cancelled.set()
                runner.revision = result['revision']
                return result

    def _readers_clean(self):
        for reader in self.readers:
            if reader.errors:
                raise reader.errors[0][1]
            require(reader.connection is None, 'prepared reader cleanup ambiguous')

    def complete(self):
        """Prepare once, clean exact objects once, then commit one terminal release."""
        require(not self.used, 'success release is single-use')
        self.used = True
        runner = self.runner
        self._proof()
        runner._fault('before_release_preparation')
        self.objects, self.binding = self._proof()
        self.binding_hash = digest(self.binding)
        prepared = self._call('prepare_release', runner.journal.prepare_release, self.binding, preparing=True)
        self.operation, self.state = prepared['operation'], 'cleanup_pending'
        runner._fault('after_release_preparation')
        # Protection is still held here; all native/capture/control authority is revoked.
        self._pending_proof()
        evidence = cleanup(self)
        runner._fault('after_release_cleanup')
        try:
            result = self._call('record_release_cleanup', runner.journal.record_release_cleanup, evidence)
        except BaseException as secondary:
            if self.first_cleanup_error is not None:
                runner._error(secondary)
                raise self.first_cleanup_error
            raise
        self.state = result['state']
        if not evidence['cleanup_complete']:
            raise self.first_cleanup_error or RuntimeError('release cleanup remains unknown')
        # New transaction owners must themselves be confirmed clean before terminal commit.
        self._readers_clean()
        runner._fault('before_terminal_release')
        value = {'preparation_operation': self.operation, 'cleanup_operation': result['operation'],
            'binding_hash': self.binding_hash, 'cleanup_complete': True, 'returned_units': 1}
        self.state = 'release_unknown'
        self.terminal_result = self._call('settle_owned_success', runner.journal.settle_owned_success, value)
        self.state = 'released'
        runner._fault('after_terminal_release')
        for reader in self.readers:
            if reader.errors:
                # A confirmed terminal commit is never undone by a reporting/close failure.
                raise reader.errors[0][1]
        return self.terminal_result

    def evidence(self):
        """Report local cleanup separately from authoritative terminal accounting."""
        readers_complete = all(r.connection is None for r in self.readers)
        return {'state': self.state, 'execution_revoked': self.runner.cancelled.is_set(),
            'cleanup_complete': self.cleanup_result is not None and self.cleanup_result['cleanup_complete']
                and readers_complete, 'resources': self.cleanup_result, 'readers': [r.evidence() for r in self.readers],
            'terminal_result': self.terminal_result}
