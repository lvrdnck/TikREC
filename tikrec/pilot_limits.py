"""Finite pilot-specific ingress limits and conservative supervised headroom."""
import shutil
import time
from threading import Lock

from .capture_control import CaptureStopped
from .flv_codec import avc_configuration_dimensions
from .source import iter_url_chunks, iter_tags
from .storage_status import GIB
from .session_journal_types import require


# Eight lifetime sessions, not just concurrent units, bound retained history/media.
MAX_SESSIONS = 8
MAX_SECONDS = 120
MAX_INPUT = 64 * 1024**2
MAX_TAGS = 4000
MAX_CHUNKS = 16384
MAX_CONNECTIONS = 4
LAUNCH_FREE = 16 * GIB
STOP_FREE = 8 * GIB
MAX_MEDIA = 6 * GIB
MAX_STATE = GIB // 2


class PilotEnvelope:
    """Observe independent disk/state budgets; ingress limits apply before raw writes."""

    def __init__(self, home, *, disk_usage=shutil.disk_usage, clock=time.monotonic):
        self.home, self.disk_usage, self.clock = home, disk_usage, clock
        self.start_time = clock()
        self.reason, self.observed = None, {}
        self.lock = Lock()

    def free(self):
        """Unknown/free-space failure cannot establish a usable operating envelope."""
        try:
            free = self.disk_usage(self.home if self.home.exists() else self.home.parent).free
            require(type(free) is int and free >= 0, 'pilot free space is unavailable')
            return free
        except Exception:
            return None

    def launch_ready(self):
        """Refuse launch/admission below the full fixed envelope, not a count guess."""
        free = self.free()
        require(free is not None and free >= LAUNCH_FREE, 'pilot requires 16 GiB free headroom')

    def inspect(self):
        """Observe retained inputs, raw/arrivals, output/scratch and state on one volume."""
        media = state = count = 0
        for path in self.home.rglob('*'):
            try:
                info = path.lstat()
            except FileNotFoundError:
                continue  # Owned publication/cleanup can move a scratch file during inspection.
            require(not path.is_symlink() and not getattr(info, 'st_file_attributes', 0) & 0x400,
                    'pilot evidence redirected; preserve state')
            count += 1
            require(count <= 100000, 'pilot evidence count exceeds envelope')
            if path.is_file():
                if path.relative_to(self.home).parts[0] == 'media':
                    media += info.st_size
                else:
                    state += info.st_size
        free = self.free()
        self.observed = {'free_bytes': free, 'media_bytes': media, 'state_bytes': state}
        if free is None or free <= STOP_FREE:
            return 'pilot_low_space_stop'
        if media >= MAX_MEDIA or state >= MAX_STATE:
            return 'pilot_byte_envelope_stop'
        if self.clock() - self.start_time >= 900:
            return 'pilot_run_duration_stop'
        return None

    def source_options(self, bridge, *, chunks=None, resolver=None):
        """Wrap trusted fixture or normal transport bytes through the original FLV parser."""
        beginning, total, tags, reads, connections = self.clock(), 0, 0, 0, 0
        def check():
            if bridge.stop_event.is_set() or self.clock() - beginning >= MAX_SECONDS:
                bridge.stop_event.set()
                raise CaptureStopped()
        def stream(url, raw=None):
            nonlocal total, tags, reads, connections
            connections += 1
            if connections > MAX_CONNECTIONS:
                bridge.stop_event.set()
                raise CaptureStopped()
            check()
            source = chunks(url, check) if chunks is not None else iter_url_chunks(
                url, chunk_size=65536, timeout=5, check_stop=check)
            def bounded():
                nonlocal total, reads
                for chunk in source:
                    check()
                    require(type(chunk) is bytes and len(chunk) <= 65536, 'pilot chunk bound exceeded')
                    if total + len(chunk) > MAX_INPUT or reads >= MAX_CHUNKS:
                        bridge.stop_event.set()
                        raise CaptureStopped()
                    total += len(chunk)
                    reads += 1
                    if raw is not None:
                        raw.write(chunk)
                    yield chunk
            data = bounded()
            try:
                for tag in iter_tags(data):
                    check()
                    tags += 1
                    # Repeated codec headers are copied to new parts; bound that amplification.
                    config = tag.is_configuration
                    if tags > MAX_TAGS or len(tag.payload) > 1024**2 or config and len(tag.payload) > 4096:
                        bridge.stop_event.set()
                        raise CaptureStopped()
                    if tag.is_avc_configuration:
                        width, height = avc_configuration_dimensions(tag.payload[5:])
                        if width > 1920 or height > 1080:
                            bridge.stop_event.set()
                            raise CaptureStopped()
                    yield tag
                if raw is not None:
                    raw.observe_read_end('eof')
            finally:
                data.close()
                source.close()
                if raw is not None:
                    raw.close()
        result = {'tag_source': lambda url: stream(url), 'raw_tag_source': stream,
                  'warning': lambda _: None, 'offline_confirmation_checks': 1,
                  'offline_confirmation_interval': 0.1, 'backoff_seconds': 0.1}
        if resolver is not None:
            result['resolver'] = resolver
        return result
