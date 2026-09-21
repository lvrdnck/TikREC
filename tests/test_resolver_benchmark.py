"""Offline safety and timing checks for the read-only resolver benchmark."""

import json
from io import StringIO

import pytest

from scripts.benchmark_bound_resolution import render_report
from tests.test_tiktok import live_page
from tests.test_tiktok_bound import (PAGE, SIGNED, _RouteOpener, page_404,
                                     public_room, room_info)
from tikrec.resolver_benchmark import benchmark_resolution


def test_compares_fast_bound_and_direct_room_info_without_exposing_transport():
    opener = _RouteOpener({
        "room:123": [room_info(), room_info()],
        "account": [public_room("123")],
    })

    report = benchmark_resolution(PAGE, "123", samples=1, opener=opener)

    pair = report["pairs"][0]
    assert sorted(item["stage"] for item in pair["bound"]["requests"]) == [
        "public_account_lookup", "room_info",
    ]
    assert [item["stage"] for item in pair["direct"]["requests"]] == ["room_info"]
    assert pair["equivalence"] == {
        "comparable": True,
        "room_id_equal": True,
        "rendition_label_equal": True,
        "rendition_source_equal": True,
        "media_transport_equal": True,
    }
    rendered = json.dumps(report)
    assert SIGNED not in rendered and "cdn.test" not in rendered and "secret" not in rendered


def test_request_and_total_timing_boundaries_are_nonnegative_and_independent():
    opener = _RouteOpener({
        "room:123": [room_info(), room_info()],
        "account": [public_room("123")],
    })

    report = benchmark_resolution(PAGE, "123", samples=1, opener=opener)

    pair = report["pairs"][0]
    for path in ("bound", "direct"):
        assert pair[path]["total_seconds"] >= 0
        assert all(item["seconds"] >= 0 for item in pair[path]["requests"])


def test_reports_public_account_lookup_for_current_fast_path():
    opener = _RouteOpener({
        "room:123": [room_info(), room_info()],
        "account": [public_room("123")],
    })

    report = benchmark_resolution(PAGE, "123", samples=1, opener=opener)

    stages = [item["stage"] for item in report["pairs"][0]["bound"]["requests"]]
    assert "public_account_lookup" in stages and "live_page" not in stages
    assert report["summary"]["bound_public_lookup_median_seconds"] is not None


def test_bound_fallback_times_page_and_rechecks_without_printing_url():
    opener = _RouteOpener({
        "room:123": [b"not json", room_info(), room_info()],
        "account": [b'{"statusCode":0,"data":{}}', public_room("123")],
        "page": [page_404()],
    })

    report = benchmark_resolution(PAGE, "123", samples=1, opener=opener)

    requests = report["pairs"][0]["bound"]["requests"]
    assert sum(item["stage"] == "room_info" for item in requests) == 2
    assert any(item["stage"] == "live_page" and not item["succeeded"] for item in requests)
    assert sum(item["stage"] == "public_account_lookup" for item in requests) == 2
    assert report["pairs"][0]["equivalence"]["comparable"] is True


def test_direct_known_room_refresh_rejects_conflicting_room_identity():
    opener = _RouteOpener({
        "room:123": [room_info(), room_info("456")],
        "account": [public_room("123")],
    })

    report = benchmark_resolution(PAGE, "123", samples=1, opener=opener)

    direct = report["pairs"][0]["direct"]
    assert direct["outcome"] == "error"
    assert direct["error_type"] == "TikTokResolutionError"
    assert report["summary"]["comparable_sample_count"] == 0


def test_different_exact_transport_is_not_a_comparable_pair_or_savings_sample():
    other = "https://cdn.test/live.flv?signature=different"
    opener = _RouteOpener({
        "room:123": [room_info(), room_info(url=other)],
        "account": [public_room("123")],
    })

    report = benchmark_resolution(PAGE, "123", samples=1, opener=opener)

    pair = report["pairs"][0]
    assert pair["equivalence"] == {
        "comparable": False,
        "room_id_equal": True,
        "rendition_label_equal": True,
        "rendition_source_equal": True,
        "media_transport_equal": False,
    }
    assert pair["direct_savings_seconds"] is None
    assert report["summary"]["comparable_sample_count"] == 0
    assert SIGNED not in json.dumps(report) and other not in json.dumps(report)


def test_direct_offline_status_remains_typed_trustworthy_evidence():
    opener = _RouteOpener({
        "room:123": [room_info(status=4)] * 3,
        "account": [public_room("123")],
        "page": [live_page("123")],
    })

    report = benchmark_resolution(PAGE, "123", samples=1, opener=opener)

    for path in ("bound", "direct"):
        run = report["pairs"][0][path]
        assert run["outcome"] == "offline"
        assert run["room_id"] == "123" and run["room_status"] == 4
        assert run["error_type"] == "TikTokOfflineError"


@pytest.mark.parametrize("malformed", [
    b"not json",
    b'{"status_code":0,"data":{"status":"unknown"}}',
    b'{"status_code":0,"data":{"status":2,"stream_url":{}}}',
])
def test_direct_malformed_or_unverifiable_response_fails_closed(malformed):
    opener = _RouteOpener({
        "room:123": [room_info(), malformed],
        "account": [public_room("123")],
    })

    report = benchmark_resolution(PAGE, "123", samples=1, opener=opener)

    direct = report["pairs"][0]["direct"]
    assert direct["outcome"] == "error"
    assert direct["error_type"] == "TikTokResolutionError"
    assert report["pairs"][0]["equivalence"]["comparable"] is False


def test_current_different_room_semantics_are_not_bypassed_by_direct_success():
    opener = _RouteOpener({
        "room:123": [room_info(), room_info()],
        "room:456": [room_info("456")],
        "account": [public_room("456"), public_room("456")],
        "page": [b"<html>no room identity</html>"],
    })

    report = benchmark_resolution(PAGE, "123", samples=1, opener=opener)

    pair = report["pairs"][0]
    assert pair["bound"]["outcome"] == "different_room"
    assert pair["bound"]["room_id"] == "456"
    assert pair["direct"]["outcome"] == "live"
    assert pair["equivalence"]["comparable"] is False
    assert pair["direct_savings_seconds"] is None


def test_benchmark_does_not_mutate_capture_or_session_evidence(tmp_path):
    manifest = tmp_path / "session.json"
    connections = tmp_path / "connections.jsonl"
    manifest.write_bytes(b'{"status":"recording"}\n')
    connections.write_bytes(b'{"connection":1}\n')
    before = (manifest.read_bytes(), connections.read_bytes())
    opener = _RouteOpener({
        "room:123": [room_info(), room_info()],
        "account": [public_room("123")],
    })

    benchmark_resolution(PAGE, "123", samples=1, opener=opener)

    assert (manifest.read_bytes(), connections.read_bytes()) == before
    assert sorted(path.name for path in tmp_path.iterdir()) == [
        "connections.jsonl", "session.json",
    ]


def test_text_report_contains_only_safe_equivalence_and_timing_facts():
    opener = _RouteOpener({
        "room:123": [room_info(label=SIGNED), room_info(label=SIGNED)],
        "account": [public_room("123")],
    })
    report = benchmark_resolution(PAGE, "123", samples=1, opener=opener)
    output = StringIO()

    render_report(report, stdout=output)

    text = output.getvalue()
    assert "Saved room ID: 123" in text and "media_transport_equal" not in text
    assert SIGNED not in text and "cdn.test" not in text and "secret" not in text


@pytest.mark.parametrize("samples", [0, 21, True, 1.5])
def test_benchmark_sample_count_is_strictly_bounded(samples):
    with pytest.raises(ValueError, match="samples"):
        benchmark_resolution(PAGE, "123", samples=samples, opener=_RouteOpener({}))
