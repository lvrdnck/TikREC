"""A first successful resolution may precede its first manifest write."""

import json

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
