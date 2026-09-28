"""Read-only retention inventory reports only proven stable file sizes."""

import json
import os

from tests.test_retention_plan import NOW, inspect, session
from tikrec.configuration import Configuration
from tikrec.retention_plan import plan_retention


def test_inventory_counts_output_and_parts_without_changing_bytes(tmp_path):
    parts = session(tmp_path, "alpha")
    before = {path: path.read_bytes() for path in (tmp_path / "alpha.mp4", *parts.iterdir())}
    item = plan_retention(tmp_path, Configuration(retention_max_age_days=1),
                          clock=lambda: NOW, media_inspector=inspect)["sessions"][0]
    assert item["classification"] == "eligible"
    assert item["file_count"] == len(before)
    assert item["flv_part_count"] == 1
    assert item["final_output_bytes"] == (tmp_path / "alpha.mp4").stat().st_size
    assert item["retained_parts_bytes"] == sum(path.stat().st_size for path in parts.iterdir())
    assert item["total_file_bytes"] == sum(len(content) for content in before.values())
    assert {path: path.read_bytes() for path in before} == before


def test_unproven_inventory_is_null_not_zero(tmp_path):
    parts = session(tmp_path, "alpha")
    output = tmp_path / "alpha.mp4"
    output.unlink()
    item = plan_retention(tmp_path, Configuration(retention_max_age_days=1),
                          clock=lambda: NOW, media_inspector=inspect)["sessions"][0]
    assert item["classification"] != "eligible"
    assert all(item[name] is None for name in (
        "file_count", "flv_part_count", "final_output_bytes",
        "retained_parts_bytes", "total_file_bytes"))
    assert parts.exists()


def test_ambiguous_hardlinked_inventory_is_null(tmp_path):
    parts = session(tmp_path, "alpha")
    source = next(parts.glob("part-*.flv"))
    alias = tmp_path / "alias.flv"
    os.link(source, alias)
    item = plan_retention(tmp_path, Configuration(retention_max_age_days=1),
                          clock=lambda: NOW, media_inspector=inspect)["sessions"][0]
    assert item["file_count"] is None and item["total_file_bytes"] is None
    assert json.loads((parts / "session.json").read_text())["creator"] == "alpha"
