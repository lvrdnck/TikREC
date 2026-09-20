"""Offline checks for extracted LIVE connection source selection."""

from types import SimpleNamespace
from urllib.error import HTTPError

import pytest

from tikrec.live_recovery import SourceRefreshError
from tikrec.live_source import connection_source


def test_custom_source_keeps_url_and_warns_when_raw_copy_unavailable(tmp_path):
    warnings, seen = [], []
    tags = iter(())
    def source(url):
        seen.append(url)
        return tags
    result, raw = connection_source(
        "direct", number=3, raw_copy_dir=tmp_path, raw_tag_source=None,
        tag_source=source, observation=None, control=None, warning=warnings.append,
    )
    assert list(result) == [] and raw is None and seen == ["direct"]
    assert warnings == ["raw copy is unavailable for a custom tag source"]


def test_custom_raw_source_keeps_connection_number(tmp_path):
    seen = []
    def source(url, raw):
        seen.append((url, raw))
        return iter(())
    tags, raw = connection_source(
        "direct", number=3, raw_copy_dir=tmp_path, raw_tag_source=source,
        tag_source=None, observation=SimpleNamespace(), control=None,
        warning=lambda message: None,
    )
    assert list(tags) == [] and seen == [("direct", raw)]
    raw.close()


def test_lazy_media_404_requests_identity_refresh_without_offline_claim():
    def source(url):
        yield from ()
        raise HTTPError(url, 404, "missing", {}, None)
    tags, _ = connection_source(
        "https://cdn.test/live.flv", number=1, raw_copy_dir=None,
        raw_tag_source=None, tag_source=source, observation=None, control=None,
        warning=lambda message: None,
    )
    with pytest.raises(SourceRefreshError):
        list(tags)
