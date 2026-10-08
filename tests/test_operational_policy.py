"""Fresh-space protection is independent of completed history and HTTP traffic."""
from types import SimpleNamespace

import pytest

from tikrec.operational_policy import OperatingPolicy, GIB


def test_pressure_thresholds_and_unknown_storage(tmp_path):
    (tmp_path / 'state').mkdir(); (tmp_path / 'media').mkdir()
    free = [30 * GIB]
    policy = OperatingPolicy(tmp_path, 10, disk_usage=lambda _: SimpleNamespace(free=free[0]))
    assert policy.reason('admission') is None
    free[0] = 13 * GIB
    assert policy.reason('admission') == 'low_free_space'
    assert policy.reason('finalization') is None
    free[0] = 11 * GIB
    assert policy.reason('finalization') == 'low_free_space'
    assert policy.reason('capture') is None
    free[0] = 10 * GIB
    assert policy.reason('capture') == 'low_free_space'
    free[0] = None
    assert policy.reason('capture') == 'storage_unavailable'


def test_no_lifetime_duration_or_input_byte_ceiling(tmp_path):
    (tmp_path / 'state').mkdir(); (tmp_path / 'media').mkdir()
    policy = OperatingPolicy(tmp_path, 1, disk_usage=lambda _: SimpleNamespace(free=30 * GIB))
    assert policy.reason('capture') is None
    assert not hasattr(policy, 'start_time')
    assert not hasattr(policy, 'max_sessions')
    assert policy.writer_budget() == 27 * GIB


def test_configured_maximum_reserve_keeps_additional_admission_headroom(tmp_path):
    policy = OperatingPolicy(tmp_path, 1024)
    assert policy.storage('media').minimum_free_bytes == 1028 * GIB


def test_diagnostic_ring_is_bounded_and_unknown_events_refused(tmp_path, monkeypatch):
    from tikrec import operational_diagnostics
    from tikrec.operational_diagnostics import Diagnostics
    monkeypatch.setattr(operational_diagnostics, 'SEGMENT_BYTES', 4096)
    log = Diagnostics(tmp_path)
    for _ in range(500):
        log.emit('observation', free_bytes=100, paused_reason=None)
    assert len(list(tmp_path.glob('events-*.jsonl'))) == 4
    assert sum(p.stat().st_size for p in tmp_path.glob('events-*.jsonl')) <= 4 * 4096
    with pytest.raises(ValueError):
        log.emit('observation', token='secret')
