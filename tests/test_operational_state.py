"""Operational profile refuses missing/foreign state and preserves pilot boundaries."""
import json
import os
from pathlib import Path
from uuid import uuid4

import pytest

from tikrec.operational_state import ServiceState
from tikrec.operational_state import KnownAutomationStore
from tikrec.automation_state import AutomationState, AutomationStateError

pytestmark = pytest.mark.skipif(os.name != 'nt', reason='native Windows directory ownership')


def test_known_reopen_no_recreation_and_automation_replacement(tmp_path):
    home = tmp_path / 'home'; catalog = str(uuid4())
    source = {'checkout': str(Path(__file__).absolute().parents[1]), 'source_sha256': 'fixture'}
    state = ServiceState(home)
    try:
        state.open('init', catalog, source)
        marker = (home / 'service.json').read_bytes()
    finally:
        assert state.close()

    # Atomic automation saves do not change stable directory/catalog marker identity.
    state.automation.save(AutomationState(consumed_rooms=(('fixture.creator', '1234'),)))
    state = ServiceState(home)
    try:
        state.open('reopen', catalog, source)
        assert state.automation.load().consumed() == {'fixture.creator': '1234'}
        assert (home / 'service.json').read_bytes() == marker
    finally:
        assert state.close()
    (home / 'automation' / 'automation.json').unlink()
    state = ServiceState(home)
    try:
        with pytest.raises(ValueError):
            state.open('reopen', catalog, source)
        assert not (home / 'automation' / 'automation.json').exists()
    finally:
        assert state.close()


def test_automation_growth_refuses_before_replacement_and_missing_save_never_recreates(tmp_path):
    path = tmp_path / 'automation.json'
    store = KnownAutomationStore(path); store.initialize()
    original = path.read_bytes()
    state = AutomationState(consumed_rooms=tuple((f'creator{i:06}', '1' * 20) for i in range(40000)))
    with pytest.raises(AutomationStateError):
        store.save(state)
    assert path.read_bytes() == original
    path.unlink()
    with pytest.raises(AutomationStateError):
        store.save(AutomationState())
    assert not path.exists()


@pytest.mark.parametrize('conflict', ['catalog', 'source', 'pilot', 'corrupt'])
def test_foreign_or_conflicting_marker_refuses_without_rewriting(tmp_path, conflict):
    home = tmp_path / 'home'; catalog = str(uuid4())
    source = {'checkout': str(Path(__file__).absolute().parents[1]), 'source_sha256': 'fixture'}
    state = ServiceState(home)
    try:
        state.open('init', catalog, source)
    finally:
        assert state.close()
    path = home / 'service.json'
    if conflict == 'pilot':
        path.rename(home / 'pilot.json')
    elif conflict == 'corrupt':
        path.write_text('{}')
    elif conflict == 'source':
        source = {**source, 'source_sha256': 'different'}
    else:
        catalog = str(uuid4())
    before = {p: p.read_bytes() for p in home.rglob('*') if p.is_file()}
    state = ServiceState(home)
    try:
        with pytest.raises(ValueError):
            state.open('reopen', catalog, source)
        assert all(p.read_bytes() == value for p, value in before.items())
    finally:
        assert state.close()
