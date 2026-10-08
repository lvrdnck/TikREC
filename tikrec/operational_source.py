"""Continuous capture transport with bounded per-read/parser/metadata allocation."""
from .capture_control import CaptureStopped
from .flv_codec import avc_configuration_dimensions
from .media import inspect_media
from .source import iter_tags, iter_url_chunks, SourceStallError
from .session_journal_types import require


def source_options(policy, bridge, ffprobe, retry_policy, *, chunks=None, resolver=None):
    """Keep ordinary retries/cadence and check storage before every raw/retained write."""
    connections = configurations = replays = 0
    previous = {}

    def check():
        if bridge.stop_event.is_set():
            raise CaptureStopped()
        if policy.reason('capture'):
            # The original UUID gets a durable interrupted stop, never a fake room end.
            policy.stop_capture(bridge)
            raise CaptureStopped()

    def stream(url, raw=None):
        nonlocal connections, configurations, replays
        connections += 1
        # Metadata lists in the accepted capture pipeline must remain finite.
        require(connections <= 512, 'operational connection metadata bound reached')
        previous.clear()
        check()
        source = chunks(url, check) if chunks is not None else iter_url_chunks(
            url, chunk_size=65536, timeout=5, check_stop=check)

        def guarded():
            for chunk in source:
                check()
                require(type(chunk) is bytes and len(chunk) <= 65536, 'operational read bound exceeded')
                if raw is not None:
                    raw.write(chunk)
                yield chunk

        data = guarded()
        try:
            for tag in iter_tags(data):
                check()
                require(len(tag.payload) <= 1024**2 and
                        (not tag.is_configuration or len(tag.payload) <= 4096),
                        'operational parser envelope exceeded')
                if tag.is_configuration:
                    configurations += 1
                    require(configurations <= 1024, 'operational part metadata bound reached')
                if tag.is_media:
                    if tag.timestamp < previous.get(tag.tag_type, 0):
                        replays += 1
                        require(replays <= 1024, 'operational replay metadata bound reached')
                    previous[tag.tag_type] = tag.timestamp
                if tag.is_avc_configuration:
                    width, height = avc_configuration_dimensions(tag.payload[5:])
                    require(min(width, height) > 0 and max(width, height) <= 1920
                            and min(width, height) <= 1080, 'operational decoder envelope exceeded')
                yield tag
            if raw is not None:
                raw.observe_read_end('eof')
        except SourceStallError:
            if raw is not None:
                raw.observe_read_end('timeout')
            raise
        except Exception:
            if raw is not None:
                raw.observe_read_end('error')
            raise
        finally:
            data.close()
            source.close()
            if raw is not None:
                raw.close()

    result = {'tag_source': lambda url: stream(url), 'raw_tag_source': stream,
              'retry_policy': retry_policy, 'warning': lambda _: None,
              'media_inspector': lambda path: inspect_media(path, ffprobe=str(ffprobe))}
    if resolver is not None:
        result['resolver'] = resolver
    return result
