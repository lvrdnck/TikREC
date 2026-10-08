"""Pilot ingress/headroom boundaries independent of runtime scheduling."""
from pathlib import Path
from threading import Event
from types import SimpleNamespace

import pytest

from tikrec import pilot_limits
from tikrec.capture_control import CaptureStopped
from tikrec.pilot_limits import PilotEnvelope, GIB
from tikrec.session_journal_types import JournalError


def test_headroom_launch_and_early_stop_are_distinct(tmp_path):
    free = [16 * GIB]
    env = PilotEnvelope(tmp_path, disk_usage=lambda _: SimpleNamespace(free=free[0]))
    env.launch_ready()
    free[0] = 12 * GIB
    with pytest.raises(JournalError):
        env.launch_ready()
    assert env.inspect() is None
    free[0] = 8 * GIB
    assert env.inspect() == 'pilot_low_space_stop'


@pytest.mark.parametrize('free', [None, -1, 1.5, 'unknown'])
def test_unknown_space_cannot_prove_an_envelope(tmp_path, free):
    env = PilotEnvelope(tmp_path, disk_usage=lambda _: SimpleNamespace(free=free))
    with pytest.raises(JournalError):
        env.launch_ready()
    assert env.inspect() == 'pilot_low_space_stop'


def test_media_and_state_limits_count_actual_bytes(tmp_path, monkeypatch):
    (tmp_path / 'media').mkdir()
    file = tmp_path / 'media' / 'generated.bin'
    file.write_bytes(b'generated')
    monkeypatch.setattr(pilot_limits, 'MAX_MEDIA', 9)
    env = PilotEnvelope(tmp_path, disk_usage=lambda _: SimpleNamespace(free=100 * GIB))
    assert env.inspect() == 'pilot_byte_envelope_stop'
    assert env.observed['media_bytes'] == 9


def test_input_limit_precedes_raw_write_and_preserves_original_prefix(tmp_path, monkeypatch):
    from tests.capture_handoff_helpers import local_media
    data = local_media(tmp_path / 'fixture.flv')
    monkeypatch.setattr(pilot_limits, 'MAX_INPUT', 512)
    bridge = SimpleNamespace(stop_event=Event())
    raw = SimpleNamespace(chunks=[], write=lambda value: raw.chunks.append(value),
                          close=lambda: None, observe_read_end=lambda _: None)
    def chunks(_, check):
        for offset in range(0, len(data), 256):
            yield data[offset:offset + 256]
    env = PilotEnvelope(tmp_path)
    source = env.source_options(bridge, chunks=chunks)['raw_tag_source']('', raw)
    with pytest.raises(CaptureStopped):
        list(source)
    assert bridge.stop_event.is_set()
    assert b''.join(raw.chunks) == data[:512]


def test_duration_stop_before_any_network_or_raw_open(tmp_path):
    clock = [0]
    env = PilotEnvelope(tmp_path, clock=lambda: clock[0])
    bridge = SimpleNamespace(stop_event=Event())
    options = env.source_options(bridge, chunks=lambda *_: pytest.fail('source opened'))
    clock[0] = 120
    with pytest.raises(CaptureStopped):
        list(options['tag_source'](''))
    assert bridge.stop_event.is_set()
