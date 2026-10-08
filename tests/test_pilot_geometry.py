"""Real generated AVC/AAC geometry admission through the unchanged FLV parser."""
from dataclasses import replace
from threading import Event
from types import SimpleNamespace

import pytest

from tests.pilot_test_helpers import generate
from tikrec.capture_control import CaptureStopped
from tikrec.flv_codec import FlvFormatError, avc_configuration_dimensions
from tikrec.pilot_limits import PilotEnvelope
from tikrec.source import iter_tags


def limited(base, data):
    """Keep the real parser and raw sink, replacing only transport bytes."""
    bridge = SimpleNamespace(stop_event=Event())
    raw = SimpleNamespace(chunks=[], write=lambda chunk: raw.chunks.append(chunk),
                          close=lambda: None, observe_read_end=lambda _: None)
    options = PilotEnvelope(base).source_options(bridge, chunks=lambda *_:
        (data[offset:offset + 256] for offset in range(0, len(data), 256)))
    return bridge, raw, options['raw_tag_source']('', raw)


@pytest.mark.parametrize('size', ['640x1280', '720x1280', '1080x1920',
                                 '1920x1080', '1280x720', '64x64'])
def test_real_orientation_independent_bound_preserves_tags_and_raw(tmp_path, size):
    generate(tmp_path, (size, size))
    data = (tmp_path / 'one.flv').read_bytes()
    bridge, raw, source = limited(tmp_path, data)
    tags = list(source)
    assert tags == list(iter_tags([data]))
    configurations = [tag for tag in tags if tag.is_avc_configuration]
    assert configurations
    assert avc_configuration_dimensions(configurations[0].payload[5:]) == tuple(map(int, size.split('x')))
    assert not bridge.stop_event.is_set() and b''.join(raw.chunks) == data


@pytest.mark.parametrize('size', ['1922x1080', '1082x1920', '2560x1440', '1280x1280'])
def test_real_out_of_envelope_geometry_refuses_configuration(tmp_path, size):
    generate(tmp_path, (size, size))
    data = (tmp_path / 'one.flv').read_bytes()
    bridge, raw, source = limited(tmp_path, data)
    yielded = []
    with pytest.raises(CaptureStopped):
        for tag in source:
            yielded.append(tag)
    assert bridge.stop_event.is_set()
    assert not any(tag.is_avc_configuration for tag in yielded)
    assert data.startswith(b''.join(raw.chunks))


@pytest.mark.parametrize('configuration', [b'\x01', b'\x01\x64\x00\x1f\xff\xe0\x00'])
def test_malformed_unprovable_configuration_remains_refused(tmp_path, configuration):
    generate(tmp_path)
    data = (tmp_path / 'one.flv').read_bytes()
    tags = [replace(tag, payload=tag.payload[:5] + configuration) if tag.is_avc_configuration else tag
            for tag in iter_tags([data])]
    corrupted = data[:13] + b''.join(tag.encoded() for tag in tags)
    _, _, source = limited(tmp_path, corrupted)
    with pytest.raises(FlvFormatError):
        list(source)


@pytest.mark.parametrize('dimensions', [(0, 64), (64, 0), (-1, 64)])
def test_nonpositive_parser_fact_cannot_establish_bound(tmp_path, monkeypatch, dimensions):
    from tikrec import pilot_limits
    generate(tmp_path)
    monkeypatch.setattr(pilot_limits, 'avc_configuration_dimensions', lambda _: dimensions)
    bridge, _, source = limited(tmp_path, (tmp_path / 'one.flv').read_bytes())
    with pytest.raises(CaptureStopped):
        list(source)
    assert bridge.stop_event.is_set()
