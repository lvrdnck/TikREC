"""Actual process death and a second recovery restart preserve exact accounting."""

import ctypes as C
import hashlib
import json
import os
import sys
from pathlib import Path

import pytest

from tests.journal_assembly_helpers import managed_process, queue_media
from tests.journal_recovery_helpers import hashes
from tests.journal_settlement_helpers import adapter_for, independent_cleanup
from tests.owned_process_helpers import Events
from tikrec.capture_handoff_authority import CaptureAuthority
from tikrec.capture_handoff_native import NativeHandle
from tikrec.owned_process_api import H, check, kernel
from tikrec.session_journal import SessionJournal


pytestmark = pytest.mark.skipif(os.name != 'nt', reason='actual Windows supervisor death')


def _kill(api, process):
    """Terminate a blocked disposable supervisor and verify its true process exit."""
    api.TerminateProcess.argtypes, api.TerminateProcess.restype = [H, C.c_uint32], C.c_int
    check(api.TerminateProcess(process.native.process, 73))
    assert api.WaitForSingleObject(process.native.process, 10000) == 0
    assert process.wait(10).state == 'confirmed_exited'


def _wait_for_barrier(barrier, process):
    """Include bounded supervisor diagnostics if setup exits before its barrier."""
    try:
        # Full generated capture/assembly/validation setup can exceed the default 10s.
        # The actual native event remains required; this is no product phase deadline.
        barrier.wait(timeout_ms=30000)
    except AssertionError as error:
        evidence = process.poll()
        raise AssertionError(f'{error}; supervisor={evidence.state}; '
            f'stdout={evidence.stdout.decode(errors="replace")!r}; '
            f'stderr={evidence.stderr.decode(errors="replace")!r}') from error


def _child_import_path(monkeypatch):
    repository = str(Path(__file__).resolve().parents[1])
    inherited = os.environ.get('PYTHONPATH', '')
    monkeypatch.setenv('PYTHONPATH', os.pathsep.join(part for part in (repository, inherited) if part))


def test_actual_prepared_death_and_second_recovery_crash_finish_fifo(
        tmp_path, managed_process, monkeypatch):
    _child_import_path(monkeypatch)
    api = kernel()
    with Events() as prepared_barrier:
        supervisor = managed_process()
        supervisor.start(Path(sys._base_executable), ['-m', 'tests.journal_settlement_death_probe',
            'before_terminal_release', str(tmp_path), *prepared_barrier.names], cwd=tmp_path,
            before_resume=lambda value: value)
        _wait_for_barrier(prepared_barrier, supervisor)
        context = json.loads((tmp_path / 'context.json').read_text(encoding='utf-8'))
        _kill(api, supervisor)
    journal = SessionJournal(Path(context['path']), context['catalog'])
    assert journal.settlement(context['token'])['state'] == 'cleanup_confirmed'
    with CaptureAuthority(journal, Path(context['root'])) as owner:
        _, later = queue_media(owner, tmp_path, different=True, name='recovery-next', room='456')
    before_recovery = hashes(Path(context['root']))
    output = Path(context['requested_final'])
    output_hash = hashlib.sha256(output.read_bytes()).hexdigest()
    boundaries = [('after_recovery_authority', 'authorized'), ('after_recovery_proof', 'proved'),
        ('after_recovery_cleanup', 'proved'), ('after_recovery_cleanup_record', 'cleaned'),
        ('before_recovery_terminal', 'cleaned'), ('after_recovery_terminal', 'released')]
    for generation, (mode, state) in enumerate(boundaries, 1):
        with Events() as recovery_barrier:
            recovery = managed_process()
            recovery.start(Path(sys._base_executable), ['-m', 'tests.release_recovery_death_probe',
                mode, str(tmp_path / 'context.json'), *recovery_barrier.names], cwd=tmp_path,
                before_resume=lambda value: value)
            _wait_for_barrier(recovery_barrier, recovery)
            recovery_context = json.loads((tmp_path / 'recovery-context.json').read_text(encoding='utf-8'))
            assert recovery_context['generation'] == generation and recovery_context['state'] == state
            _kill(api, recovery)
        journal = SessionJournal(Path(context['path']), context['catalog'])
        assert journal.release_recovery(context['token'])['head']['state'] == state
        assert journal.settlement(context['token'])['state'] == ('released' if state == 'released'
                                                                  else 'cleanup_confirmed')
    assert len(journal.status()['units']) == 1
    owner = CaptureAuthority(journal, Path(context['root']))
    adapter = None
    try:
        result = owner.recover_prepared_release(context['session'], context['token'])
        assert result['state'] == 'released'
        assert result['recovery_result']['evidence']['generation'] == 6
        assert journal.release_recovery(context['token'])['head']['generation'] == 6
        assert hashes(Path(context['root'])) == before_recovery
        assert hashlib.sha256(output.read_bytes()).hexdigest() == output_hash
        manifest, history = Path(context['manifest']), Path(context['history'])
        for path, expected in context['hashes'].items():
            original = history if path == str(manifest) else Path(path)
            assert hashlib.sha256(original.read_bytes()).hexdigest() == expected
        before_repeat = journal.path.read_bytes()
        with monkeypatch.context() as patch:
            patch.setattr(NativeHandle, '__init__', lambda *_a, **_k: pytest.fail('released retry reopened media'))
            assert owner.recover_prepared_release(context['session'], context['token']) == result
        assert journal.path.read_bytes() == before_repeat
        adapter = adapter_for(owner, managed_process)
        next_result = adapter.run()
        assert next_result['session_id'] == later['id'] and next_result['state'] == 'released'
        assert journal.status()['units'] == []
    finally:
        if adapter is not None:
            independent_cleanup(adapter)
        owner.close()


@pytest.mark.parametrize(('mode', 'state'), [
    ('after_release_resource_input_0', 'cleanup_pending'),
    ('cleanup_incomplete_after_cleanup_receipt', 'cleanup_incomplete')])
def test_pending_or_incomplete_original_cleanup_recovers_after_supervisor_death(
        tmp_path, managed_process, monkeypatch, mode, state):
    _child_import_path(monkeypatch)
    api = kernel()
    with Events() as barrier:
        supervisor = managed_process()
        supervisor.start(Path(sys._base_executable), ['-m', 'tests.journal_settlement_death_probe',
            mode, str(tmp_path), *barrier.names], cwd=tmp_path,
            before_resume=lambda value: value)
        _wait_for_barrier(barrier, supervisor)
        context = json.loads((tmp_path / 'context.json').read_text(encoding='utf-8'))
        _kill(api, supervisor)
    journal = SessionJournal(Path(context['path']), context['catalog'])
    original = journal.settlement(context['token'])
    assert original['state'] == state
    if state == 'cleanup_incomplete':
        assert not original['cleanup']['evidence']['cleanup_complete']
    before = hashes(Path(context['root']))
    output = Path(context['requested_final'])
    output_hash = hashlib.sha256(output.read_bytes()).hexdigest()
    owner = CaptureAuthority(journal, Path(context['root']))
    try:
        result = owner.recover_prepared_release(context['session'], context['token'])
        assert result['state'] == 'released'
        assert journal.release_recovery(context['token'])['head']['generation'] == 1
        assert hashes(Path(context['root'])) == before
        assert hashlib.sha256(output.read_bytes()).hexdigest() == output_hash
        assert journal.settlement(context['token'])['cleanup'] == original['cleanup']
        assert journal.status()['units'] == []
    finally:
        owner.close()
