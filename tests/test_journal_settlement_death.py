"""Actual supervisor deaths distinguish prepared, cleaned and released accounting."""

import ctypes as C
import hashlib
import json
import os
import sys
from uuid import uuid4
from pathlib import Path

import pytest

from tests.owned_process_helpers import Events, managed_process
from tikrec.owned_process_api import H, check, kernel
from tikrec.session_journal import SessionJournal

pytestmark = pytest.mark.skipif(os.name != 'nt', reason='actual Windows supervisor death')


@pytest.mark.parametrize('mode,state', [
    ('before_release_preparation', None), ('prepare_release_before_commit', None),
    ('prepare_release_after_commit', 'cleanup_pending'), ('after_release_preparation', 'cleanup_pending'),
    ('after_release_resource_input_0', 'cleanup_pending'),
    ('after_release_resource_scratch_candidate.mp4', 'cleanup_pending'),
    ('after_release_resource_lease', 'cleanup_pending'), ('after_release_cleanup', 'cleanup_pending'),
    ('record_release_cleanup_before_commit', 'cleanup_pending'),
    ('record_release_cleanup_after_commit', 'cleanup_confirmed'), ('before_terminal_release', 'cleanup_confirmed'),
    ('settle_owned_success_after_terminal', 'cleanup_confirmed'),
    ('settle_owned_success_after_unit_release', 'cleanup_confirmed'),
    ('settle_owned_success_after_claim_release', 'cleanup_confirmed'),
    ('settle_owned_success_before_commit', 'cleanup_confirmed'),
    ('settle_owned_success_after_commit', 'released'), ('after_terminal_release', 'released'),
])
def test_actual_death_never_infers_cleanup_or_replays_accounting(tmp_path, managed_process, mode, state):
    api = kernel()
    api.TerminateProcess.argtypes, api.TerminateProcess.restype = [H, C.c_uint32], C.c_int
    with Events() as barrier:
        supervisor = managed_process()
        supervisor.start(Path(sys._base_executable), ['-m', 'tests.journal_settlement_death_probe',
            mode, str(tmp_path), *barrier.names], cwd=tmp_path, before_resume=lambda value: value)
        barrier.wait()
        context = json.loads((tmp_path / 'context.json').read_text(encoding='utf-8'))
        check(api.TerminateProcess(supervisor.native.process, 73))
        assert api.WaitForSingleObject(supervisor.native.process, 10000) == 0
        assert supervisor.wait(10).state == 'confirmed_exited'
        store = SessionJournal(Path(context['path']), context['catalog'])
        before = store.path.read_bytes()
        record = store.settlement(context['token'])
        assert (record is not None) == (state is not None)
        if state is not None:
            assert record['state'] == state
        manifest, history = Path(context['manifest']), Path(context['history'])
        original_hashes = {}
        for path, expected in context['hashes'].items():
            original = history if path == str(manifest) else Path(path)
            original_hashes[path] = hashlib.sha256(original.read_bytes()).hexdigest()
            assert original_hashes[path] == expected
        completion = store.manifest_completion(context['token'])
        from tikrec.manifest_successor_values import unpacked
        assert history.read_bytes() == unpacked(completion['binding']['predecessor'])
        assert manifest.read_bytes() == unpacked(completion['binding']['successor'])
        candidate = store.scratch(context['token'])['candidate']
        output_hash = hashlib.sha256(Path(context['requested_final']).read_bytes()).hexdigest()
        assert output_hash == candidate['sha256']
        assert candidate['publication'] == 'unpublished' and candidate['validation'] == 'not_checked'
        session = store.session(context['session'])
        terminal = state == 'released'
        for field in ('seal', 'seal_hash', 'intent', 'generation', 'origin_slot'):
            assert session[field] == context['original'][field]
        assert session['task']['state'] == session['phase'] == ('completed' if terminal else 'running')
        assert len(store.status()['units']) == (0 if terminal else 1)
        assert session['rooms'] == ([] if terminal else context['original']['rooms'])
        assert session['artifacts'] == ([] if terminal else context['original']['artifacts'])
        assert store.owned_attempt(context['token'])['state'] == ('held' if state is None else 'revoked')
        assert store.path.read_bytes() == before
        assert store.claim_owned(str(uuid4()), str(uuid4()), str(uuid4())) is None
        # No next queued task exists; the null claim receipt is an explicit new operation.
        after_claim = store.path.read_bytes()
        assert store.settlement(context['token']) == record and store.path.read_bytes() == after_claim
        assert store.path.read_bytes() != before
        (tmp_path / 'settlement-death-evidence.json').write_text(json.dumps({'mode': mode, 'state': state,
            'record': record, 'accounting': store.status(), 'output_hash': output_hash,
            'original_hashes': original_hashes, 'read_only_inspection_unchanged': True}, indent=2), encoding='utf-8')
