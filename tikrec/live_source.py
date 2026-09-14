"""Open one LIVE connection with the existing optional raw-copy behavior."""

from .capture import raw_copy_path
from .source import RawCopy, iter_url_tags
from .live_recovery import SourceNetworkError
from .network_errors import classify_failure


def connection_source(direct_url, *, number, raw_copy_dir, raw_tag_source,
                      tag_source, observation, control, warning):
    """Identify errors originating in transport, without disguising writer disk errors."""
    try:
        tags, raw = _connection_source(direct_url, number=number, raw_copy_dir=raw_copy_dir,
            raw_tag_source=raw_tag_source, tag_source=tag_source, observation=observation,
            control=control, warning=warning)
    except Exception as error:
        if classify_failure(error, transport=True).category == "transient":
            raise SourceNetworkError(error) from error
        raise
    return _guard_tags(tags), raw


def _guard_tags(tags):
    try:
        yield from tags
    except Exception as error:
        if classify_failure(error, transport=True).category == "transient":
            raise SourceNetworkError(error) from error
        raise
    finally:
        close = getattr(tags, "close", None)
        if close is not None:
            close()


def _connection_source(direct_url, *, number, raw_copy_dir, raw_tag_source,
                       tag_source, observation, control, warning):
    """Return the source and optional raw copy without changing reconnect policy."""
    raw_copy = None
    if raw_copy_dir is not None and raw_tag_source is not None:
        raw_copy = RawCopy(
            raw_copy_path(raw_copy_dir, number),
            warning,
        )
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
        )
        tags = iter_url_tags(direct_url, raw_copy=raw_copy, on_open=observation.opened,
                             check_stop=control.check)
    else:
        if raw_copy_dir is not None:
            warning("raw copy is unavailable for a custom tag source")
        tags = (iter_url_tags(direct_url, on_open=observation.opened,
                             check_stop=control.check)
                if tag_source is iter_url_tags else tag_source(direct_url))
    return tags, raw_copy
