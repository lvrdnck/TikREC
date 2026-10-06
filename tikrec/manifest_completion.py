"""One live publication -> exact control successor, with retained native owners."""

import json
from contextlib import contextmanager
from dataclasses import asdict

from .manifest_guard import check_inputs
from .manifest_native import create_stage, write_stage
from .manifest_successor_values import packed, successor_bytes
from .publication_native import rename_no_replace
from .session_journal_types import ArtifactIdentity, digest, encode, require


class ManifestCompletion:
    """Unreconstructible one-shot capability over original input/output/control objects."""

    def __init__(self, publication):
        self.publication, self.runner = publication, publication.coordinator
        runner = self.runner
        require(getattr(runner, 'manifest_capable', False) and publication.used and publication.error is None
                and publication.capability is not None and publication.capability.moved
                and getattr(runner, 'manifest_owner', None) is None, "live completion-capable publication required")
        runner.manifest_owner = self
        self.stage, self.operation, self.used = None, None, False
        self.stage_owner, self.stage_handle, self.stage_fd = None, None, None
        self.preserved, self.installed, self.written = False, False, False
        self.guard = runner.guard
        self.predecessor_index = next(i for i, a in enumerate(self.guard.seal.artifacts)
                                      if a.identity.components[-1] == 'session.json')
        self.predecessor = self.guard.files[self.predecessor_index]
        require(self.predecessor.control_right, 'original control transition rights unavailable')
        self.original_handle = self.predecessor.handle
        self.parent = self.guard.directory
        self.parent_handle = self.parent.handle
        self.manifest = self.parent.path / 'session.json'
        self.history = self.parent.path / f'.tikrec-manifest-{runner.token}.original.json'
        self.stage_name = f'.tikrec-manifest-{runner.token}.successor.json'
        def identity(name):
            return ArtifactIdentity(self.parent.identity.volume, self.parent.identity.components + (name.casefold(),))
        self.history_identity, self.stage_identity = identity(self.history.name), identity(self.stage_name)
        self.manifest_identity = identity('session.json')
        publication.capability.revalidate()
        observed = runner.journal.publication(runner.token)
        require(observed is not None and observed['evidence'] is not None
                and observed['operation'] == publication.capability.operation, 'fresh publication result missing')
        owner = runner.journal.owned_attempt(runner.token)
        self.binding = {k: owner[k] for k in ('session_id', 'token', 'owner', 'h_operation',
                                            'h_revision', 'seal_hash', 'marker_hash')}
        old = self.predecessor.read_control()
        self.successor = successor_bytes(old, runner.journal.session(owner['session_id']),
                                        observed['binding']['validation']['evidence']['report'])
        self.binding.update(publication=observed, predecessor={**packed(old),
            'identity': asdict(self.predecessor.identity), 'size': self.predecessor.size, 'stamp': self.predecessor.stamp},
            successor=packed(self.successor), namespace={'parent': asdict(self.parent.identity),
                'manifest': 'session.json', 'history': self.history.name, 'stage': self.stage_name})
        self.binding = json.loads(encode(self.binding))

    def _live(self):
        self.publication.capability._live()
        require(self.runner.manifest_owner is self and self.runner.guard is self.guard
                and self.guard.files[self.predecessor_index] is self.predecessor
                and self.predecessor.handle == self.original_handle and self.parent is self.guard.directory
                and self.parent.handle == self.parent_handle, 'manifest live owner revoked')
        if self.stage is not None and self.stage.handle is not None:
            require(self.stage is self.stage_owner and self.stage.handle == self.stage_handle
                    and self.stage.fd == self.stage_fd, 'manifest successor owner replaced')

    def check_inputs(self):
        """Permit only this exact control chain; generic guards remain unchanged."""
        return check_inputs(self)

    def revalidate(self):
        """Fresh output/input/control proof brackets every native/journal mutation."""
        self._live()
        self.publication.capability.revalidate()
        require(self.runner.journal.publication(self.runner.token) == self.binding['publication'],
                'manifest publication evidence changed')
        if self.operation is not None:
            record = self.runner.journal.manifest_completion(self.runner.token)
            require(record is not None and record['operation'] == self.operation
                    and record['binding'] == self.binding, 'manifest preparation changed')
        if not self.preserved:
            require(not self.history.exists() and not self.history.is_symlink(), 'manifest history collision')
        if self.stage is None:
            path = self.parent.path / self.stage_name
            require(not path.exists() and not path.is_symlink(), 'manifest stage collision')

    @contextmanager
    def _fence(self, count):
        with self.runner.gate:
            self._live()
            with self.runner.journal.manifest_fence(self.runner.token, self.runner.owner, self.runner.revision,
                    self.operation, digest(self.binding), count):
                yield

    def _retain(self, owner):
        self.stage = self.stage_owner = owner
        self.guard.extra_handles.append(owner)

    def _record(self, phase, held):
        self.revalidate()
        evidence = {'state': phase, 'preparation_operation': self.operation, 'binding_hash': digest(self.binding),
            'identity': json.loads(encode(asdict(held.identity))), 'size': held.size, 'stamp': held.stamp,
            'sha256': packed(held.read_control())['sha256'], 'required_flushed': phase != 'preserved'}
        self.runner._fault('before_manifest_' + phase + '_result')
        self.revalidate()
        self.runner._transition('manifest_step', self.runner.journal.manifest_step, phase, evidence)
        self.runner._fault('after_manifest_' + phase + '_result')
        self.revalidate()
        return evidence

    def complete(self):
        """Prepare, stage, preserve and install once; retain uncertainty without rollback."""
        require(not self.used, 'manifest completion is single-use')
        self.used = True
        runner = self.runner
        self.revalidate()
        runner._fault('before_manifest_preparation')
        self.revalidate()
        result = runner._transition('prepare_manifest', runner.journal.prepare_manifest, self.binding)
        self.operation = result['operation']
        self.guard.manifest_successor = self
        runner._fault('after_manifest_preparation')
        self.revalidate()
        runner._fault('before_manifest_create')
        self.revalidate()
        with self._fence(0):
            create_stage(self.parent, self.stage_name, self._retain)
            self.stage_handle, self.stage_fd = self.stage.handle, self.stage.fd
        runner._fault('after_manifest_create')
        self.revalidate()
        runner._fault('before_manifest_write')
        self.revalidate()
        with self._fence(0):
            write_stage(self.stage, self.successor)
            self.written, self.staged_stamp = True, self.stage.stamp
        runner._fault('after_manifest_write')
        self._record('staged', self.stage)
        runner._fault('before_manifest_preserve')
        self.revalidate()
        with self._fence(1):
            rename_no_replace(self.predecessor, self.parent, self.history.name)
            self.preserved = True
            self.predecessor.path, self.predecessor.identity = self.history, self.history_identity
        runner._fault('after_manifest_preserve')
        self._record('preserved', self.predecessor)
        runner._fault('before_manifest_install')
        self.revalidate()
        with self._fence(2):
            rename_no_replace(self.stage, self.parent, 'session.json')
            self.installed = True
            self.stage.path, self.stage.identity = self.manifest, self.manifest_identity
        runner._fault('after_manifest_install')
        self.revalidate()
        runner._fault('before_manifest_flush')
        self.revalidate()
        with self._fence(2):
            self.stage.flush()
        runner._fault('after_manifest_flush')
        return self._record('installed', self.stage)
