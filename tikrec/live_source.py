"""Open one LIVE connection with the existing optional raw-copy behavior."""

import time
from contextlib import nullcontext
from urllib.error import HTTPError

from .capture import raw_copy_path
from .source import RawCopy, iter_url_tags
from .live_recovery import SourceNetworkError, SourceRefreshError
from .network_errors import classify_failure
from .capture_fence import FencedRaw


def connection_source(direct_url, *, number, raw_copy_dir, raw_tag_source,
                      tag_source, observation, control, warning, fence=None):
    """Identify errors originating in transport, without disguising writer disk errors."""
    try:
        with fence.opening() if fence is not None else nullcontext():
            tags, raw = _connection_source(direct_url, number=number, raw_copy_dir=raw_copy_dir,
                raw_tag_source=raw_tag_source, tag_source=tag_source, observation=observation,
                control=control, warning=warning, fence=fence)
    except Exception as error:
        if isinstance(error, HTTPError) and error.code == 404:
            raise SourceRefreshError(error) from error
        if classify_failure(error, transport=True).category == "transient":
            raise SourceNetworkError(error) from error
        raise
    return _guard_tags(tags if fence is None else fence.iterator(tags)), raw


def _guard_tags(tags):
    try:
        yield from tags
    except Exception as error:
        if isinstance(error, HTTPError) and error.code == 404:
            raise SourceRefreshError(error) from error
        if classify_failure(error, transport=True).category == "transient":
            raise SourceNetworkError(error) from error
        raise
    finally:
        close = getattr(tags, "close", None)
        if close is not None:
            close()


def _connection_source(direct_url, *, number, raw_copy_dir, raw_tag_source,
                       tag_source, observation, control, warning, fence=None):
    """Return the source and optional raw copy without changing reconnect policy."""
    raw_copy = None
    if raw_copy_dir is not None and raw_tag_source is not None:
        raw_copy = RawCopy(
            raw_copy_path(raw_copy_dir, number),
            warning,
            connection_number=number,
            wall_clock=getattr(observation, "clock", time.time),
        )
        if fence is not None:
            raw_copy = FencedRaw(raw_copy, fence)
        try:
            tags = raw_tag_source(direct_url, raw_copy)
        except BaseException:
            # An injected source can fail before returning the iterator its caller would close.
            raw_copy.close()
            raise
    elif raw_copy_dir is not None and tag_source is iter_url_tags:
        raw_copy = RawCopy(
            raw_copy_path(raw_copy_dir, number),
            warning,
            connection_number=number,
            wall_clock=getattr(observation, "clock", time.time),
        )
        if fence is not None:
            raw_copy = FencedRaw(raw_copy, fence)
        tags = iter_url_tags(direct_url, raw_copy=raw_copy, on_open=observation.opened,
                             check_stop=control.check)
    else:
        if raw_copy_dir is not None:
            warning("raw copy is unavailable for a custom tag source")
        tags = (iter_url_tags(direct_url, on_open=observation.opened,
                             check_stop=control.check)
                if tag_source is iter_url_tags else tag_source(direct_url))
    return tags, raw_copy
