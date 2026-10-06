"""Fresh no-follow read protection and exact output/control proof for recovery."""

import hashlib
import json
import os
from dataclasses import asdict
from pathlib import Path

from .capture_handoff_marker import validate_pending_values
from .capture_handoff_native import NativeHandle
from .release_recovery_handles import NativeCloseGuard
from .session_journal_recovery_checks import expected_inventory
from .session_journal_types import encode, require


class RecoveryNativeProof:
    """Open only the prepared resource list and prove it under new native handles."""

    def __init__(self, recovery):
        self.recovery = recovery
        self.objects, self.acquired = {}, set()
        self.extra_owners = recovery.extra_owners

    def open_all(self):
        """Reopen the immutable prepared scope without writes or path adoption."""
        for resource in self.recovery.binding['resources']:
            self.recovery._check_cancelled()
            if resource['kind'] == 'native':
                self._open_resource(resource)
                self.recovery.fault('after_recovery_resource_' + resource['key'].replace(':', '_'))

    def _open_resource(self, resource):
        key, proof = resource['key'], resource['evidence']
        directory = key in {'input:0', 'input:2', 'scratch:workspace'}
        options = {'directory': True} if directory else {'read_only': True}
        if key == 'input:1':
            options = {'shared': True}
        held = NativeHandle.__new__(NativeHandle)
        held.ever_acquired = False
        self.objects[key] = held
        try:
            NativeHandle.__init__(held, Path(proof['path']), **options,
                cleanup_guard_factory=lambda handle: NativeCloseGuard(self.recovery, handle, resource_key=key))
        except BaseException as error:
            self.extra_owners.extend(getattr(error, 'capture_native_owners', ()))
            if held.ever_acquired:
                self.acquired.add(key)
            raise
        self.acquired.add(key)
        held.verify()
        identity = {'volume': held.identity.volume, 'components': list(held.identity.components)}
        require(identity == proof['identity'], 'recovery opened another native object')
        if not directory:
            require(held.size == proof['size'] and held.stamp == proof['stamp'],
                    'recovery file identity or stamp drifted')

    def _names(self, directory):
        names = []
        for path in directory.path.iterdir():
            self.recovery._check_cancelled()
            names.append(path.name.casefold())
            require(len(names) <= 4097, 'recovery directory inventory is ambiguous')
        require(len(names) <= 4097 and len(names) == len(set(names)),
                'recovery directory inventory is ambiguous')
        return sorted(names)

    @staticmethod
    def _hash(held, *, check=lambda: None):
        require(held.fd is not None and held.read_only, 'recovery output is not a held read-only file')
        os.lseek(held.fd, 0, os.SEEK_SET)
        digestor = hashlib.sha256()
        while True:
            check()
            block = os.read(held.fd, 1024 * 1024)
            if not block:
                break
            digestor.update(block)
        os.lseek(held.fd, 0, os.SEEK_SET)
        return digestor.hexdigest()

    def verify(self):
        """Recheck all held media/control bytes and exact post-install inventories."""
        recovery = self.recovery
        recovery._check_cancelled()
        authority, journal = recovery.authority, recovery.view
        authority.assert_held()
        recovery.lease.assert_held()
        for key, held in self.objects.items():
            recovery._check_cancelled()
            held.verify()
            expected = next(item for item in recovery.binding['resources'] if item['key'] == key)['evidence']
            identity = {'volume': held.identity.volume, 'components': list(held.identity.components)}
            require(identity == expected['identity'], 'recovery resource was replaced')
            if key not in {'input:0', 'input:2', 'scratch:workspace'}:
                require(held.size == expected['size'] and held.stamp == expected['stamp'],
                        'recovery resource changed while held')
        owner_row = journal.owned_attempt(recovery.token)
        session = journal.session(recovery.session_id)
        require(session is not None and session['id'] == owner_row['session_id'] == recovery.session_id
                and session['phase'] == 'running' and session['task']['state'] == 'running'
                and owner_row['state'] == 'revoked', 'prepared task ownership changed')
        owner_row['seal'] = session['seal']
        expected_parts, expected_scratch = expected_inventory(owner_row, recovery.binding)
        parts = self._names(self.objects['input:2'])
        scratch = self._names(self.objects['scratch:workspace'])
        require(parts == expected_parts and scratch == expected_scratch,
                'recovery parts or scratch namespace changed')
        seal = session['seal']
        control_hashes = []
        for index, artifact in enumerate(seal['artifacts'], 3):
            if artifact['control_hash'] is not None:
                control = self.objects[f'input:{index}']
                observed = hashlib.sha256(control.read_control()).hexdigest()
                require(observed == artifact['control_hash'], 'sealed control bytes changed')
                control_hashes.append({'key': f'input:{index}', 'sha256': observed})
        predecessor_index = next(index for index, artifact in enumerate(seal['artifacts'], 3)
                                 if artifact['identity']['components'][-1] == 'session.json')
        history = self.objects[f'input:{predecessor_index}'].read_control()
        installed = self.objects['manifest:successor'].read_control()
        manifest = recovery.binding['manifest']['binding']
        from .manifest_successor_values import unpacked
        predecessor_bytes = unpacked(manifest['predecessor'])
        successor_bytes = unpacked(manifest['successor'])
        require(history == predecessor_bytes and installed == successor_bytes,
                'installed manifest or preserved capture truth changed')
        marker_key = f'input:{len(seal["artifacts"]) + 3}'
        marker_data = self.objects[marker_key].read_control()
        marker = json.loads(marker_data)
        h_receipt = journal.operation(owner_row['h_operation'])
        validate_pending_values(authority, recovery.session_id, session, marker, h_receipt)
        marker_hash = hashlib.sha256(marker_data).hexdigest()
        require(marker['operation'] == owner_row['h_operation'] and marker_hash == owner_row['marker_hash'],
                'original H marker changed')
        control_hashes.extend(({'key': marker_key, 'sha256': marker_hash},
            {'key': 'manifest:successor', 'sha256': hashlib.sha256(installed).hexdigest()}))
        output = self.objects['scratch:candidate.mp4']
        output_hash = self._hash(output, check=recovery._check_cancelled)
        require(output_hash == recovery.binding['publication']['evidence']['sha256'],
                'completed output bytes changed')
        # Recheck after the long hash so drift during that scan cannot escape.
        require(self._names(self.objects['input:2']) == parts
                and self._names(self.objects['scratch:workspace']) == scratch,
                'recovery parts or scratch namespace changed')
        for held in self.objects.values():
            recovery._check_cancelled()
            held.verify()
        current = journal.settlement(recovery.token)
        require(current['preparation'] == recovery.record['preparation']
                and current['cleanup'] == recovery.record['cleanup'] and current['state'] != 'released',
                'prepared release changed during recovery proof')
        resources = []
        for resource in recovery.binding['resources']:
            key = resource['key']
            if resource['kind'] == 'lease':
                lease = recovery.lease
                evidence = {'mode': lease.mode, 'slot': lease.slot,
                    'identity': list(lease.identity), 'root': str(lease.root)}
            else:
                held = self.objects[key]
                evidence = {'path': str(held.path), 'identity': asdict(held.identity),
                    'size': held.size, 'stamp': held.stamp}
            resources.append({'key': key, 'kind': resource['kind'], 'evidence': evidence})
        return json.loads(encode({'schema_version': 1, 'session_id': recovery.session_id, 'token': recovery.token,
            'generation': recovery.generation, 'authority': recovery.authority_id,
            'preparation_operation': recovery.preparation_operation,
            'binding_hash': recovery.binding_hash, 'resources': resources,
            'controls': control_hashes, 'output_sha256': output_hash,
            'parts_inventory': parts, 'scratch_inventory': scratch}))

    @staticmethod
    def same_proof(before, after):
        """Compare stable directory identities, exact files and complete inventories."""
        def stable(value):
            result = json.loads(encode(value))
            for resource in result['resources']:
                if resource['key'] in {'input:0', 'input:2', 'scratch:workspace'}:
                    evidence = resource['evidence']
                    # Windows parent metadata changes when unrelated children are created.
                    evidence['size'] = 0
                    evidence['stamp'] = ':'.join(evidence['stamp'].split(':')[:2])
            return result
        return stable(before) == stable(after)
