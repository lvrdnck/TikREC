"""Immutable artifact identity checks for an eligible synthetic session."""

import json
import os
from pathlib import Path

import pytest

from tests.test_retention_plan import NOW, inspect, session
from tests.test_retention_execute import fixture, events
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


@pytest.mark.skipif(os.name != "nt", reason="Windows ctime is creation time")
@pytest.mark.parametrize("change", ["protected_creator", "active_status"])
@pytest.mark.parametrize("mutate_at", [1, 2])
def test_metadata_preserving_manifest_change_stops_next_delete(
        tmp_path, change, mutate_at):
    root, parts, _, config, _, audit, run = fixture(tmp_path)
    if change == "protected_creator":
        config.save(Configuration(retention_max_age_days=1,
                                  retention_protected_creators=("bravo",)))
    manifest = parts / "session.json"
    calls = 0

    def mutate(_path):
        nonlocal calls
        calls += 1
        if calls != mutate_at:
            return
        before = manifest.stat()
        original = manifest.read_bytes()
        old, new = ((b'"creator": "alpha"', b'"creator": "bravo"')
                    if change == "protected_creator" else
                    (b'"status": "completed"', b'"status": "recording"'))
        position = original.rfind(old)
        assert position >= 0 and len(old) == len(new)
        manifest.write_bytes(original[:position] + new + original[position + len(old):])
        os.utime(manifest, ns=(before.st_atime_ns, before.st_mtime_ns))
        after = manifest.stat()
        assert (before.st_size, before.st_mtime_ns, before.st_ctime_ns,
                before.st_ino) == (after.st_size, after.st_mtime_ns,
                                   after.st_ctime_ns, after.st_ino)
        current = plan_retention(root, config.load(), clock=lambda: NOW,
                                 media_inspector=inspect)["sessions"][0]
        assert current["classification"] != "eligible"

    with pytest.raises(ValueError, match="target|control|claim"):
        run(before_mutation=mutate)
    assert calls == mutate_at and (root / "alpha.mp4").exists()
    assert events(audit)[-1]["event"] == "failed"
    assert parts.exists() and manifest.exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows ctime is creation time")
@pytest.mark.parametrize("mutate_at", [1, 2])
def test_metadata_preserving_connection_control_change_stops_next_delete(
        tmp_path, mutate_at):
    root, parts, _, config, _, audit, run = fixture(tmp_path)
    log = parts / "connections.jsonl"
    log.write_text(json.dumps({"connection": 1, "started_at": 1000,
                               "ended_at": 1005}) + "\n")
    assert plan_retention(root, config.load(), clock=lambda: NOW,
                          media_inspector=inspect)["sessions"][0]["classification"] == "eligible"
    calls = 0

    def mutate(_path):
        nonlocal calls
        calls += 1
        if calls != mutate_at:
            return
        before = log.stat()
        content = log.read_bytes()
        assert content.count(b'"ended_at": 1005') == 1
        log.write_bytes(content.replace(b'"ended_at": 1005', b'"ended_at": 1006'))
        os.utime(log, ns=(before.st_atime_ns, before.st_mtime_ns))
        after = log.stat()
        assert (before.st_size, before.st_mtime_ns, before.st_ctime_ns,
                before.st_ino) == (after.st_size, after.st_mtime_ns,
                                   after.st_ctime_ns, after.st_ino)
        if mutate_at == 1:
            # A still-eligible control change must also lose the original authority.
            assert plan_retention(root, config.load(), clock=lambda: NOW,
                                  media_inspector=inspect)["sessions"][0]["classification"] == "eligible"

    with pytest.raises(ValueError, match="target|control|claim"):
        run(before_mutation=mutate)
    assert calls == mutate_at and (root / "alpha.mp4").exists()
    assert events(audit)[-1]["event"] == "failed"
