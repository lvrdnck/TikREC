"""Recovery preserves degraded assembly truth without reprocessing media."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from tests.capture_handoff_helpers import authority
from tests.journal_assembly_helpers import managed_process
from tests.journal_recovery_helpers import hashes, prepared_success
from tests.journal_settlement_helpers import independent_cleanup


def test_recovery_preserves_degraded_input_truth(tmp_path, managed_process, monkeypatch):
    from tikrec import journal_assembly as module
    owner = authority(tmp_path)
    case = None
    try:
        build = module._build_ffmpeg_command
        def command(*args, **kwargs):
            media = build(*args, **kwargs)
            code = ('import subprocess,sys;code=subprocess.call(' + repr(media) + ");"
                    "sys.stderr.buffer.write(b'warning\\n'*4000+b'[h264 @ 0x1] corrupt slice');sys.exit(code)")
            return [sys.executable, '-c', code]
        monkeypatch.setattr(module, '_build_ffmpeg_command', command)
        case = prepared_success(owner, tmp_path, managed_process, different=True)
        manifest = Path(case['bridge'].intent.parts_path) / 'session.json'
        original = manifest.read_bytes()
        values = json.loads(original)
        assert values['finalization']['input_decode']['status'] == 'degraded'
        assert values['finalization']['input_decode']['diagnostic_count'] > 0
        before = hashes(owner.root)
        source_before = {str(path): hashlib.sha256(path.read_bytes()).hexdigest()
                         for path in tmp_path.glob('*.flv')}
        with monkeypatch.context() as patch:
            patch.setattr(subprocess, 'run', lambda *_a, **_k: pytest.fail('recovery launched a process'))
            assert owner.recover_prepared_release(case['session'], case['token'])['state'] == 'released'
        assert hashes(owner.root) == before and manifest.read_bytes() == original
        assert {str(path): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in tmp_path.glob('*.flv')} == source_before
        assert json.loads(manifest.read_bytes())['finalization']['input_decode'] == values['finalization']['input_decode']
    finally:
        if case:
            independent_cleanup(case['adapter'])
        owner.close()
