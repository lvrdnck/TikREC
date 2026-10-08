"""Bounded sanitized prospective receipts, separate from durable session evidence."""
import json
import os
import time

from .pilot_identity import local
from .session_journal_types import require

FIELDS = {'backend', 'catalog_id', 'schema', 'source', 'configuration', 'tools', 'port',
          'control', 'capacities', 'free_bytes', 'paused_reason', 'outstanding_units',
          'reason', 'primary_type', 'complete', 'captures_joined', 'finalizer_joined',
          'authority_released', 'requests_joined', 'monitor_joined', 'diagnostic_count',
          'diagnostics_dropped', 'exit_code', 'session_id', 'interrupted', 'phase'}
SEGMENT_BYTES = 1024**2


class Diagnostics:
    """Keep four one-MiB segments; never log request arguments or exception text."""

    def __init__(self, directory):
        self.directory, self.index = local(directory), 0

    def emit(self, event, **values):
        """Write an allowlisted receipt; failed sinks propagate without retrying actions."""
        require(event in {'startup', 'ready', 'observation', 'shutdown', 'exit', 'failure', 'stop'}
                and not set(values) - FIELDS, 'diagnostic fields refused')
        raw = (json.dumps({'event': event, 'at': time.time(), **values}, allow_nan=False,
                          sort_keys=True) + '\n').encode('utf-8')
        require(len(raw) <= 16384, 'diagnostic receipt exceeds bound')
        path = self.directory / ('events-' + str(self.index) + '.jsonl')
        if path.exists():
            local(path)
            require(path.stat().st_size <= SEGMENT_BYTES, 'existing diagnostic segment exceeds bound')
            if path.stat().st_size + len(raw) > SEGMENT_BYTES:
                self.index = (self.index + 1) % 4
                path = self.directory / ('events-' + str(self.index) + '.jsonl')
                if path.exists():
                    local(path)
                mode = 'wb'
            else:
                mode = 'ab'
        else:
            mode = 'xb'
        with path.open(mode) as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
