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
