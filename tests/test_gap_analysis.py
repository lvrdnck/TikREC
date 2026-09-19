"""Offline reconnect-gap calculations and boundary classification."""

from __future__ import annotations

import json
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.analyze_reconnect_gaps import analyze_paths
from tikrec.gap_analysis import analyze_records, boundary_events, summarize_gaps


def connection(number, *, started, ended, first=None, last=None, outcome="closed",
               resolved=None, opened=None, media=None):
    return {
        "connection": number, "outcome": outcome, "started_at": started, "ended_at": ended,
        "resolved_at": resolved, "http_opened_at": opened, "first_media_tag_at": media,
        "first_retained_media_at": first, "last_retained_media_at": last,
    }


def test_calculates_all_components_and_summary():
    records = (
        connection(1, started=0, ended=12, first=2, last=10),
        connection(2, started=13, ended=30, resolved=15, opened=16, media=18, first=19, last=29),
    )

    gap = analyze_records(records)[0]

    assert gap.classification == "ordinary"
    assert (gap.previous_tail_seconds, gap.local_backoff_seconds, gap.resolution_seconds) == (2, 1, 2)
    assert (gap.http_setup_seconds, gap.initial_media_seconds, gap.keyframe_gate_seconds) == (1, 2, 1)
    assert gap.total_gap_seconds == 9
    summary = summarize_gaps((gap,))
    assert summary["total_gap_seconds"].median_seconds == 9
    assert summary["total_gap_seconds"].count == 1


def test_missing_milestones_remain_unknown():
    records = (
        connection(1, started=0, ended=10, first=2, last=9),
        connection(2, started=11, ended=20, first=15, last=19),
    )

    gap = analyze_records(records)[0]

    assert gap.previous_tail_seconds == 1
    assert gap.local_backoff_seconds == 1
    assert gap.resolution_seconds is None
    assert gap.http_setup_seconds is None
    assert gap.initial_media_seconds is None
    assert gap.keyframe_gate_seconds is None
    assert gap.total_gap_seconds == 6


def test_intervening_failed_attempts_are_reported_without_double_counting_bridge():
    records = (
        connection(1, started=0, ended=10, first=1, last=9),
        connection(2, started=11, ended=13, outcome="resolver_error"),
        connection(3, started=15, ended=30, resolved=16, opened=17, media=18, first=20, last=29),
    )

    gap = analyze_records(records)[0]

    assert gap.classification == "ordinary"
    assert gap.local_backoff_seconds == 5
    assert [(attempt.connection, attempt.outcome, attempt.duration_seconds)
            for attempt in gap.intervening_attempts] == [(2, "resolver_error", 2)]
    assert gap.unrecorded_attempt_count == 0
    assert gap.total_gap_seconds == 11


def test_classifies_resume_outage_room_end_and_unrecorded_boundaries():
    first = connection(1, started=0, ended=10, first=1, last=9)
    second = connection(3, started=20, ended=30, first=22, last=29)
    cases = (
        ({"event": "capture_resume", "reason": "explicit_resume"}, "explicit_resume"),
        ({"event": "service_recovery", "reason": "process_restart"}, "service_restart"),
        ({"event": "network_recovery", "phase": "entered"}, "network_recovery"),
        ({"event": "room_status", "status": 4}, "room_end_confirmation"),
    )
    for event, expected in cases:
        gap = analyze_records((first, event, second))[0]
        assert gap.classification == expected
        assert gap.unrecorded_attempt_count == 1
    assert analyze_records((first, second))[0].classification == "other_recovery"
    assert boundary_events(tuple(event for event, _ in cases)) == (
        "capture_resume:explicit_resume", "service_recovery:process_restart",
        "network_recovery:entered", "room_status",
    )


def test_script_reads_log_without_writing_it_and_renders_unknowns():
    with TemporaryDirectory() as temporary:
        path = Path(temporary) / "connections.jsonl"
        records = (
            connection(1, started=0, ended=10, first=1, last=9),
            connection(2, started=11, ended=20, first=15, last=19),
        )
        original = "".join(json.dumps(record) + "\n" for record in records)
        path.write_text(original, encoding="utf-8")
        stdout = StringIO()

        code = analyze_paths((path,), stdout=stdout)

        assert code == 0
        assert path.read_text(encoding="utf-8") == original
        assert "1 -> 2 [ordinary]" in stdout.getvalue()
        assert "resolution_seconds: unknown" in stdout.getvalue()
