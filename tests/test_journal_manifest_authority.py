"""Committed evidence is historical; drift or failed live authority grants no write."""

import os
from pathlib import Path

import pytest

from tests.journal_manifest_helpers import completing
from tests.journal_assembly_helpers import managed_process
from tikrec.journal_manifest import ManifestCompletionError

pytestmark = pytest.mark.skipif(os.name != 'nt', reason='native Windows control authority')


@pytest.mark.parametrize('mutation', ['inventory', 'output', 'successor'])
def test_commit_window_drift_keeps_historical_result_without_live_success(completing, mutation):
    adapter, bridge, _, _, _ = completing
    runner = adapter.coordinator
    def hook(kind, point):
        if kind != 'manifest_step' or point != 'before_commit' or not runner.manifest_owner.installed:
            return
        if mutation == 'inventory':
            (Path(bridge.intent.parts_path) / 'foreign.json').write_bytes(b'new namespace occupant')
        else:
            held = runner.manifest_owner.stage if mutation == 'successor' else runner.scratch.artifacts['candidate.mp4']
            os.lseek(held.fd, 0, 0)
            os.write(held.fd, b'changed!')
            held.flush()
    runner.journal._fault = hook
    with pytest.raises(ManifestCompletionError):
        adapter.run()
    assert runner.journal.manifest_completion(runner.token)['steps'][-1]['phase'] == 'installed'
    assert not adapter.close() and runner.journal.status()['units']
    with pytest.raises(Exception):
        adapter.run()


@pytest.mark.parametrize('phase', ['prepare', 'installed'])
def test_ack_lookup_requires_fresh_proof_before_any_further_authority(completing, monkeypatch, phase):
    adapter, bridge, _, _, _ = completing
    runner, lookups = adapter.coordinator, []
    lookup = runner.journal.operation
    fired = False
    def fault(kind, point):
        nonlocal fired
        hit = kind == 'prepare_manifest' if phase == 'prepare' else kind == 'manifest_step' and runner.manifest_owner.installed
        if hit and point == 'after_commit' and not fired:
            fired = True
            raise OSError('lost acknowledgement')
    def operation(identity):
        lookups.append(identity)
        value = lookup(identity)
        (Path(bridge.intent.parts_path) / 'foreign.json').write_bytes(b'changed after acknowledgement')
        return value
    runner.journal._fault = fault
    monkeypatch.setattr(runner.journal, 'operation', operation)
    with pytest.raises(ManifestCompletionError):
        adapter.run()
    assert len(lookups) == 1
    assert phase != 'prepare' or adapter.capability.stage is None
    assert not adapter.close()


def test_failed_publication_owner_cannot_prepare_manifest(completing):
    adapter, _, _, _, _ = completing
    def hook(point):
        if point == 'after_publication_result':
            adapter.publication.error = OSError('live publication failed')
    adapter.coordinator._fault = hook
    with pytest.raises(ManifestCompletionError):
        adapter.run()
    assert adapter.coordinator.journal.publication(adapter.coordinator.token)['evidence'] is not None
    assert adapter.coordinator.journal.manifest_completion(adapter.coordinator.token) is None


@pytest.mark.parametrize('boundary', ['before_resume_fence', 'native_after_resume'])
def test_completion_validation_cancellation_on_each_side_of_resume(completing, boundary):
    adapter, _, _, _, _ = completing
    runner = adapter.coordinator
    def hook(point):
        if point == boundary and runner.children and runner.children[-1]['intent'].get('access') == 'candidate_validation':
            adapter.cancel()
    runner._fault = hook
    with pytest.raises(ManifestCompletionError):
        adapter.run()
    assert runner.journal.publication(runner.token) is None and runner.journal.manifest_completion(runner.token) is None
    assert not adapter.close() and runner.guard.retained
