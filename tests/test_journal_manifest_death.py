"""Actual supervisor death reports control facts and uncertainty without adoption."""

import base64
import ctypes as C
import hashlib
import json
import os
import sys
from pathlib import Path

import pytest

from tests.owned_process_helpers import Events, managed_process
from tikrec.owned_process_api import H, check, kernel
from tikrec.session_journal import SessionJournal

pytestmark = pytest.mark.skipif(os.name != 'nt', reason='actual Windows supervisor death')


@pytest.mark.parametrize('mode,prepared,steps,stage,preserved,installed', [
    ('before_manifest_preparation', False, 0, False, False, False),
    ('prepare_manifest_before_commit', False, 0, False, False, False),
    ('prepare_manifest_after_commit', True, 0, False, False, False),
    ('after_manifest_preparation', True, 0, False, False, False),
    ('immediately_after_create', True, 0, True, False, False),
    ('after_manifest_write', True, 0, True, False, False),
    ('manifest_step_staged_before_commit', True, 0, True, False, False),
    ('manifest_step_staged_after_commit', True, 1, True, False, False),
    ('immediately_before_preserve', True, 1, True, False, False),
    ('immediately_after_preserve', True, 1, True, True, False),
    ('manifest_step_preserved_after_commit', True, 2, True, True, False),
    ('immediately_before_install', True, 2, True, True, False),
    ('immediately_after_install', True, 2, False, True, True),
    ('after_manifest_flush', True, 2, False, True, True),
    ('manifest_step_installed_before_commit', True, 2, False, True, True),
    ('manifest_step_installed_after_commit', True, 3, False, True, True),
    ('after_manifest_installed_result', True, 3, False, True, True),
])
def test_supervisor_death_preserves_original_and_only_committed_control_facts(
        tmp_path, managed_process, mode, prepared, steps, stage, preserved, installed):
    api = kernel()
    api.TerminateProcess.argtypes, api.TerminateProcess.restype = [H, C.c_uint32], C.c_int
    with Events() as barrier:
        supervisor = managed_process()
        supervisor.start(Path(sys._base_executable), ['-m', 'tests.journal_manifest_death_probe',
            mode, str(tmp_path), *barrier.names], cwd=tmp_path, before_resume=lambda value: value)
        barrier.wait()
        context = json.loads((tmp_path / 'context.json').read_text(encoding='utf-8'))
        check(api.TerminateProcess(supervisor.native.process, 73))
        assert api.WaitForSingleObject(supervisor.native.process, 10000) == 0
        assert supervisor.wait(10).state == 'confirmed_exited'
        store = SessionJournal(Path(context['path']), context['catalog'])
        before = store.path.read_bytes()
        record = store.manifest_completion(context['token'])
        assert (record is not None) == prepared
        if prepared:
            assert len(record['steps']) == steps
        manifest, history, staged = map(Path, (context['manifest'], context['history'], context['stage']))
        assert staged.exists() == stage and history.exists() == preserved
        assert manifest.exists() == (not preserved or installed)
        for path, value in context['hashes'].items():
            original = history if path == str(manifest) and preserved else Path(path)
            assert hashlib.sha256(original.read_bytes()).hexdigest() == value
        if prepared:
            assert base64.b64decode(record['binding']['predecessor']['bytes']) == (history if preserved else manifest).read_bytes()
        if installed:
            assert manifest.read_bytes() == base64.b64decode(record['binding']['successor']['bytes'])
            assert json.loads(manifest.read_bytes())['finalization']['status'] == 'completed'
        candidate = store.scratch(context['token'])['candidate']
        assert hashlib.sha256(Path(context['requested_final']).read_bytes()).hexdigest() == candidate['sha256']
        assert candidate['publication'] == 'unpublished' and candidate['validation'] == 'not_checked'
        assert store.owned_attempt(context['token'])['state'] == 'held'
        session = store.session(context['session'])
        for key in ('seal', 'seal_hash', 'rooms', 'artifacts'):
            assert session[key] == context['original'][key]
        assert session['task']['state'] == 'running' and len(store.status()['units']) == 1
        assert store.path.read_bytes() == before
        (tmp_path / 'manifest-death-evidence.json').write_text(json.dumps({'mode': mode,
            'record': record, 'pins': store.status(), 'output_hash': candidate['sha256'],
            'original_hashes': context['hashes'], 'inspection_db_unchanged': True,
            'stage_present': stage, 'original_preserved': preserved, 'installed': installed}, indent=2), encoding='utf-8')
