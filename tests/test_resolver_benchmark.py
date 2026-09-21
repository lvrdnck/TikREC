"""Offline safety and timing checks for the read-only resolver benchmark."""

import json
from io import StringIO
from urllib.error import HTTPError

import pytest

from scripts.benchmark_bound_resolution import render_report
from tests.test_tiktok import _Opener, live_page, live_room
from tikrec.resolver_benchmark import benchmark_resolution


PAGE = "https://www.tiktok.com/@creator/live"
SIGNED = "https://cdn.test/live.flv?signature=secret"


def public_room(room_id):
    return json.dumps({"statusCode": 0, "data": {"roomId": room_id}}).encode()


def room_info(room_id="123", *, status=2, label="HD1", url=SIGNED):
    body = json.loads(live_room({label: url} if status == 2 else {}, status=status))
    body["data"]["room_id"] = room_id
    return json.dumps(body).encode()


def test_compares_bound_page_and_direct_room_info_without_exposing_transport():
    opener = _Opener([live_page("123"), room_info(), room_info()])

    report = benchmark_resolution(PAGE, "123", samples=1, opener=opener)

    pair = report["pairs"][0]
    assert [item["stage"] for item in pair["bound"]["requests"]] == [
        "live_page", "room_info",
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


def test_request_and_total_timing_boundaries_are_independent():
    ticks = iter(float(value) for value in range(10))
    opener = _Opener([live_page("123"), room_info(), room_info()])

    report = benchmark_resolution(PAGE, "123", samples=1, opener=opener,
                                  clock=lambda: next(ticks))

    pair = report["pairs"][0]
    assert [item["seconds"] for item in pair["bound"]["requests"]] == [1.0, 1.0]
    assert pair["bound"]["total_seconds"] == 5.0
    assert pair["direct"]["requests"][0]["seconds"] == 1.0
    assert pair["direct"]["total_seconds"] == 3.0


def test_reports_public_account_lookup_only_when_current_path_invokes_it():
    opener = _Opener([
        b"<html>no room identity</html>", public_room("123"), room_info(), room_info(),
    ])

    report = benchmark_resolution(PAGE, "123", samples=1, opener=opener)

    stages = [item["stage"] for item in report["pairs"][0]["bound"]["requests"]]
    assert stages == ["live_page", "public_account_lookup", "room_info"]
    assert report["summary"]["bound_public_lookup_median_seconds"] is not None


def test_bound_page_404_fallback_times_saved_room_info_without_printing_url():
    page_404 = HTTPError(PAGE, 404, "missing", {}, None)
    opener = _Opener([page_404, room_info(), room_info()])

    report = benchmark_resolution(PAGE, "123", samples=1, opener=opener)

    requests = report["pairs"][0]["bound"]["requests"]
    assert [(item["stage"], item["succeeded"]) for item in requests] == [
        ("live_page", False), ("room_info", True),
    ]
    assert report["pairs"][0]["equivalence"]["comparable"] is True


def test_direct_known_room_refresh_rejects_conflicting_room_identity():
    opener = _Opener([live_page("123"), room_info(), room_info("456")])

    report = benchmark_resolution(PAGE, "123", samples=1, opener=opener)

    direct = report["pairs"][0]["direct"]
    assert direct["outcome"] == "error"
    assert direct["error_type"] == "TikTokResolutionError"
    assert report["summary"]["comparable_sample_count"] == 0


def test_direct_offline_status_remains_typed_trustworthy_evidence():
    opener = _Opener([live_page("123"), room_info(status=4), room_info(status=4)])

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
    opener = _Opener([live_page("123"), room_info(), malformed])

    report = benchmark_resolution(PAGE, "123", samples=1, opener=opener)

    direct = report["pairs"][0]["direct"]
    assert direct["outcome"] == "error"
    assert direct["error_type"] == "TikTokResolutionError"
    assert report["pairs"][0]["equivalence"]["comparable"] is False


def test_current_different_room_semantics_are_not_bypassed_by_direct_success():
    opener = _Opener([live_page("456"), room_info("456"), room_info("123")])

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
    opener = _Opener([live_page("123"), room_info(), room_info()])

    benchmark_resolution(PAGE, "123", samples=1, opener=opener)

    assert (manifest.read_bytes(), connections.read_bytes()) == before
    assert sorted(path.name for path in tmp_path.iterdir()) == [
        "connections.jsonl", "session.json",
    ]


def test_text_report_contains_only_safe_equivalence_and_timing_facts():
    opener = _Opener([
        live_page("123"), room_info(label=SIGNED), room_info(label=SIGNED),
    ])
    report = benchmark_resolution(PAGE, "123", samples=1, opener=opener)
    output = StringIO()

    render_report(report, stdout=output)

    text = output.getvalue()
    assert "Saved room ID: 123" in text and "media_transport_equal" not in text
    assert SIGNED not in text and "cdn.test" not in text and "secret" not in text


@pytest.mark.parametrize("samples", [0, 21, True, 1.5])
def test_benchmark_sample_count_is_strictly_bounded(samples):
    with pytest.raises(ValueError, match="samples"):
        benchmark_resolution(PAGE, "123", samples=samples, opener=_Opener([]))
