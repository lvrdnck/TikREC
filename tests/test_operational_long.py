"""Accelerated generated-media evidence beyond both old ingress/time ceilings."""
import json
import os
import shutil
import subprocess
from io import BytesIO

import pytest

from tests.operational_helpers import Probe
from tests.pilot_test_helpers import wait, validate
from tikrec.flv import FlvTag, read_tag
from tikrec.session_journal import SessionJournal

pytestmark = pytest.mark.skipif(os.name != 'nt', reason='native generated Windows media')


def test_generated_121_second_70_mib_source_has_no_pilot_cutoff(tmp_path):
    subprocess.run([shutil.which('ffmpeg'), '-v', 'error', '-f', 'lavfi', '-i',
        'testsrc=size=64x64:rate=10', '-f', 'lavfi', '-i', 'sine=sample_rate=44100',
        '-t', '121', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-g', '10', '-c:a', 'aac',
        '-f', 'flv', str(tmp_path / 'input.flv')], capture_output=True, check=True, timeout=60)
    # Valid AMF0 long-string script padding tests raw ingress size, not high video bitrate.
    payload = b'\x02\x00\x04noop\x0c' + (900000).to_bytes(4, 'big') + b'x' * 900000
    padding = FlvTag(18, 0, b'\0\0\0', payload).encoded()
    with (tmp_path / 'long.flv').open('wb') as output:
        data = (tmp_path / 'input.flv').read_bytes()
        output.write(data[:13])
        for _ in range(80):
            output.write(padding)
        output.write(data[13:])
    assert (tmp_path / 'long.flv').stat().st_size > 64 * 1024**2
    probe = Probe(tmp_path).launch(init=True).launch()
    try:
        probe.ready(); value = probe.start('long', True); sid = value['session_id']
        wait(lambda: probe.client.status(sid)['output_completed'], seconds=180)
        parts = probe.home / 'media' / 'long.parts'
        assert sum(p.stat().st_size for p in parts.glob('*.raw')) == (tmp_path / 'long.flv').stat().st_size
        assert not probe.client.status(sid)['interrupted']
        manifest = json.loads((parts / 'session.json').read_text())
        assert manifest['elapsed_seconds'] >= 130
        result = subprocess.run([shutil.which('ffprobe'), '-v', 'error', '-show_entries',
            'format=duration', '-of', 'json', str(probe.home / 'media' / 'long.mp4')],
            text=True, capture_output=True, check=True, timeout=30)
        assert float(json.loads(result.stdout)['format']['duration']) >= 121
        probe.control(); probe.finish()
        validate(parts, tmp_path)
    finally:
        probe.stop()
