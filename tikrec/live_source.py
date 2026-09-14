"""Open one LIVE connection with the existing optional raw-copy behavior."""

from .capture import raw_copy_path
from .source import RawCopy, iter_url_tags


def connection_source(direct_url, *, number, raw_copy_dir, raw_tag_source,
                      tag_source, observation, control, warning):
    """Return the source and optional raw copy without changing reconnect policy."""
    raw_copy = None
    if raw_copy_dir is not None and raw_tag_source is not None:
        raw_copy = RawCopy(
            raw_copy_path(raw_copy_dir, number),
            warning,
        )
        tags = raw_tag_source(direct_url, raw_copy)
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
