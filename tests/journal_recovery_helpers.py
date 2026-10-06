"""Generated prepared successes for narrow recovery tests; never production data."""

import hashlib

import pytest

from tests.capture_handoff_helpers import local_media, observations, reserve
from tests.journal_assembly_helpers import queue_media
from tests.journal_settlement_helpers import adapter_for
from tikrec.journal_settlement import SettlementError


def prepared_success(owner, tmp_path, managed_process, *, different=False, later=False, interrupted=False):
    """Reach durable cleanup-confirmed preparation while retaining only closed originals."""
    if interrupted:
        from tikrec.source import iter_tags
        data = local_media(tmp_path / 'recover-source.flv')
        bridge = reserve(owner, 'recover-first', room='123')
        def source(_, raw):
            raw.write(data)
            yield from iter_tags((data,))
            bridge.stop()
        assert bridge.run(**observations(data, source=source)).phase == 'queued'
        first = owner.journal.session(bridge.intent.session_id)
    else:
        bridge, first = queue_media(owner, tmp_path, different=different, name='recover-first', room='123')
    later_bridge = later_session = None
    if later:
        later_bridge, later_session = queue_media(owner, tmp_path, different=different,
                                                  name='recover-later', room='456')
    adapter = adapter_for(owner, managed_process)
    adapter.coordinator._fault = lambda point: (_raise(point)
        if point == 'before_terminal_release' else None)
    with pytest.raises(SettlementError):
        adapter.run()
    runner = adapter.coordinator
    record = owner.journal.settlement(runner.token)
    assert record['state'] == 'cleanup_confirmed'
    assert runner.closed and adapter.capability.state == 'cleanup_confirmed'
    return {'owner': owner, 'adapter': adapter, 'bridge': bridge, 'first': first,
        'later_bridge': later_bridge, 'later': later_session, 'token': runner.token,
        'session': first['id'], 'record': record}


def _raise(point):
    """Stop at the ordinary pre-terminal boundary after all original resources close."""
    raise RuntimeError('prepared release boundary: ' + point)


def hashes(root):
    """Capture every small generated output/control byte sequence outside the journal."""
    return {str(path): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in root.rglob('*') if path.is_file() and path.name != '.tikrec-lifecycle.lock'}
