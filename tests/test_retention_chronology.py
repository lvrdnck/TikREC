"""A first successful resolution may precede its first manifest write."""

import json

import pytest

from tikrec.retention_chronology import coherent_chronology


def test_first_connection_crossing_manifest_start_requires_resolution_proof(tmp_path):
    log = tmp_path / "connections.jsonl"
    record = {"connection": 1, "started_at": 995, "resolved_at": 998,
              "http_opened_at": 1001, "ended_at": 1005}
    log.write_text(json.dumps(record) + "\n")
    assert coherent_chronology(tmp_path, 1000, 1010)
    record.pop("resolved_at")
    log.write_text(json.dumps(record) + "\n")
    assert not coherent_chronology(tmp_path, 1000, 1010)


def test_pre_manifest_http_and_media_are_impossible(tmp_path):
    record = {"connection": 1, "started_at": 995, "resolved_at": 996,
              "http_opened_at": 997, "first_media_tag_at": 998,
              "first_retained_media_at": 999, "ended_at": 1005}
    (tmp_path / "connections.jsonl").write_text(json.dumps(record) + "\n")
    assert not coherent_chronology(tmp_path, 1000, 1010)


@pytest.mark.parametrize("records,expected", [
    ([{"connection": 1, "started_at": 995, "resolved_at": 996,
       "http_opened_at": 1001, "first_media_tag_at": 1002,
       "first_retained_media_at": 1003, "ended_at": 1005}], True),
    ([{"connection": 1, "started_at": 990, "ended_at": 994,
       "outcome": "resolver_error"},
      {"connection": 2, "started_at": 995, "resolved_at": 996,
       "http_opened_at": 1001, "ended_at": 1005}], True),
    ([{"connection": 1, "started_at": 995, "http_opened_at": 1001,
       "ended_at": 1005}], False),
    ([{"connection": 1, "started_at": 1000, "ended_at": 1002},
      {"connection": 2, "started_at": 995, "resolved_at": 996,
       "ended_at": 1005}], False),
    ([{"connection": 1, "started_at": 995, "resolved_at": 996,
       "ended_at": 1005}], True),
])
def test_pre_manifest_resolution_boundary(tmp_path, records, expected):
    (tmp_path / "connections.jsonl").write_text(
        "".join(json.dumps(record) + "\n" for record in records))
    assert coherent_chronology(tmp_path, 1000, 1010) is expected


def test_post_start_resolver_error_cannot_claim_successful_media(tmp_path):
    record = {"connection": 1, "started_at": 1000, "resolved_at": 1001,
              "http_opened_at": 1002, "first_media_tag_at": 1003,
              "first_retained_media_at": 1004, "part_start": "part-0001.flv",
              "part_end": "part-0001.flv", "outcome": "resolver_error",
              "ended_at": 1005}
    (tmp_path / "connections.jsonl").write_text(json.dumps(record) + "\n")
    assert not coherent_chronology(tmp_path, 1000, 1010)


def test_clean_post_start_resolver_error_then_success_is_coherent(tmp_path):
    """Only contradictory success evidence is barred from resolver failures."""
    records = [
        {"connection": 1, "started_at": 1000, "ended_at": 1002,
         "outcome": "resolver_error"},
        {"connection": 2, "started_at": 1002, "resolved_at": 1003,
         "ended_at": 1005, "outcome": "room_offline"},
    ]
    (tmp_path / "connections.jsonl").write_text(
        "".join(json.dumps(record) + "\n" for record in records))
    assert coherent_chronology(tmp_path, 1000, 1010)


@pytest.mark.parametrize("field,value", [
    ("resolved_at", 1001), ("http_opened_at", 1001),
    ("first_media_tag_at", 1001), ("rendition_label", "hd"),
    ("part_start", "part-0001.flv"), ("part_timings", [{"name": "part-0001.flv"}]),
    ("raw_copy", "connection-0001.flv"),
])
def test_resolver_error_rejects_every_success_evidence_field(tmp_path, field, value):
    record = {"connection": 1, "started_at": 1000, "ended_at": 1002,
              "outcome": "resolver_error", field: value}
    (tmp_path / "connections.jsonl").write_text(json.dumps(record) + "\n")
    assert not coherent_chronology(tmp_path, 1000, 1010)
