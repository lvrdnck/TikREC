"""Source/state/secret/tool refusal and explicit known-catalog reopening."""
import json
import os
import shutil
import subprocess
from pathlib import Path
from uuid import uuid4

import pytest

pytestmark = pytest.mark.skipif(os.name != 'nt', reason='native Windows pilot')
from tikrec import pilot
from tikrec.pilot_identity import local, source_identity, check_tools
from tikrec.pilot_state import PilotState
from tikrec.session_journal_types import JournalError

ROOT = Path(__file__).absolute().parents[1]


def identity():
    """Read explicit current source identity without selecting another checkout."""
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    return source_identity(ROOT, head)


def test_wrong_import_root_or_revision_refuses():
    with pytest.raises(JournalError):
        source_identity(ROOT.parent, '0' * 40)
    with pytest.raises(JournalError):
        source_identity(ROOT, '0' * 40)


@pytest.mark.parametrize('value', ['relative', r'\\server\share\pilot', r'C:\missing-pilot-parent\home'])
def test_implicit_network_or_missing_paths_refuse(value):
    with pytest.raises((JournalError, OSError)):
        local(Path(value))


def test_tools_are_usable_explicit_and_unavailable_tool_refuses(tmp_path):
    tools = check_tools(Path(shutil.which('ffmpeg')), Path(shutil.which('ffprobe')))
    assert tools['ffmpeg']['version'].startswith('ffmpeg version')
    assert len(tools['ffprobe']['sha256']) == 64
    with pytest.raises((JournalError, OSError)):
        check_tools(tmp_path / 'missing.exe', Path(shutil.which('ffprobe')))


def test_fresh_known_catalog_reopen_and_refusal_preserve_state(tmp_path):
    home, catalog, source = tmp_path / 'home', str(uuid4()), identity()
    state = PilotState(home)
    try:
        state.open('init', catalog, source)
        assert not state.journal.history()
    finally:
        assert state.close()
    before = (home / 'pilot.json').read_bytes()
    reopened = PilotState(home)
    try:
        reopened.open('reopen', catalog, source)
        assert reopened.automation.load().pending_claim is None
    finally:
        assert reopened.close()
    for mode, cid in [('init', catalog), ('reopen', str(uuid4()))]:
        refused = PilotState(home)
        try:
            with pytest.raises(JournalError):
                refused.open(mode, cid, source)
        finally:
            assert refused.close()
    assert (home / 'pilot.json').read_bytes() == before


def test_manifest_identity_drift_is_not_recreation(tmp_path):
    state = PilotState(tmp_path / 'home'); source = identity(); catalog = str(uuid4())
    state.open('init', catalog, source); assert state.close()
    path = state.home / 'pilot.json'; document = json.loads(path.read_text())
    document['identities'][str(state.home)][1] += 1
    path.write_text(json.dumps(document))
    refused = PilotState(state.home)
    try:
        with pytest.raises(JournalError):
            refused.open('reopen', catalog, source)
    finally:
        assert refused.close()
    assert json.loads(path.read_text()) == document


def test_pilot_native_pin_failed_close_requires_exact_reference_retirement(tmp_path):
    from tests.test_release_recovery_windows_close import protection
    state = PilotState(tmp_path / 'home')
    state.open('init', str(uuid4()), identity())
    held = state.pins[-1]; native = held.handle
    protection(native, True)
    try:
        assert not state.close()
        assert held.handle == native and any(g.retained for g in state.native_close_guards)
        assert not state.close()
    finally:
        protection(native, False)
    assert state.close()
    assert all(not g.retained for g in state.native_close_guards)


def test_pilot_lifetime_admission_does_not_refund_completed_history(monkeypatch):
    from types import SimpleNamespace
    from tikrec.pilot_composition import PilotController
    from tikrec.recording import RecordingBusy
    runtime = SimpleNamespace(journal=SimpleNamespace(history=lambda **_: [{}] * 8))
    monkeypatch.setattr('tikrec.service_http_projection.RuntimeHTTPController.health',
                        lambda _: {'admission_available': True, 'active_count': 0})
    controller = PilotController(runtime, SimpleNamespace(free=lambda: 100 * 1024**3))
    with pytest.raises(RecordingBusy):
        controller.start('unused', 'unused')
    health = controller.health()
    assert health['active_count'] == 0 and not health['admission_available']
    assert health['admission_reason'] == 'pilot_lifetime_limit'
