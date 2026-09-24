"""Immutable artifact identity checks for an eligible synthetic session."""

import json
from pathlib import Path

import pytest

from tests.test_retention_plan import NOW, inspect, session
from tikrec.configuration import Configuration
from tikrec.retention_authorization import authorize, check_fingerprint, fingerprint
from tikrec.retention_locality import local_volume
from tikrec.retention_plan import plan_retention


def test_authorization_binds_exact_order_and_rejects_later_hardlink(tmp_path):
    parts = session(tmp_path, "alpha")
    config = Configuration(retention_max_age_days=1)
    item = plan_retention(tmp_path, config, clock=lambda: NOW,
                          media_inspector=inspect)["sessions"][0]
    auth = authorize(tmp_path, item, config)
    assert auth.session_id == json.loads((parts / "session.json").read_text())["session_id"]
    assert [artifact.relative_path for artifact in auth.order][-3:] == [
        str(Path("alpha.parts") / "session.json"),
        "alpha.parts", "alpha.mp4"]
    media = next(parts.glob("part-*.flv"))
    (parts / "other.flv").hardlink_to(media)
    with pytest.raises(ValueError):
        check_fingerprint(tmp_path, auth.order[0], auth.volume)


def test_fingerprint_refuses_multiply_linked_file(tmp_path):
    original = tmp_path / "output.mp4"
    original.write_bytes(b"output")
    (tmp_path / "alias.mp4").hardlink_to(original)
    with pytest.raises(ValueError, match="unsafe"):
        fingerprint(tmp_path, original, directory=False, volume=local_volume(tmp_path))
