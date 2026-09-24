"""Bounded claim snapshots must retain content identity across equal metadata."""

import json
import os

from tests.test_retention_plan import session
from tikrec.retention_snapshot import capture_claim, capture_root


def test_same_size_manifest_change_with_restored_mtime_changes_root_snapshot(tmp_path):
    directory = session(tmp_path, "alpha")
    initial = capture_root(tmp_path, capture_claim)
    manifest = directory / "session.json"
    before = manifest.stat()
    replacement = manifest.read_bytes().replace(b'"creator": "alpha"', b'"creator": "bravo"')
    assert len(replacement) == before.st_size  # Metadata alone is insufficient.
    manifest.write_bytes(replacement)
    os.utime(manifest, ns=(before.st_atime_ns, before.st_mtime_ns))
    current = capture_root(tmp_path, capture_claim)
    assert initial != current
    assert initial.claims[0].manifest_digest != current.claims[0].manifest_digest


def test_missing_and_explicit_null_output_are_distinct(tmp_path):
    directory = session(tmp_path, "alpha", output=False)
    manifest = directory / "session.json"
    values = json.loads(manifest.read_text())
    values["output_path"] = None
    manifest.write_text(json.dumps(values))
    absent = capture_claim(directory, tmp_path)
    assert absent.output_state == "null" and not absent.uncertain
    values.pop("output_path")
    manifest.write_text(json.dumps(values))
    missing = capture_claim(directory, tmp_path)
    assert missing.output_state == "unknown" and missing.uncertain
