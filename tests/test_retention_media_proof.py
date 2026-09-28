"""Destructive retention must keep ordinary validated media byte-bound."""

import os
from pathlib import Path

import pytest

from tests.test_retention_execute import events, fixture
from tests.test_retention_plan import MEDIA, NOW, inspect
from tikrec.retention_plan import plan_retention


def _change_bytes(path):
    before = path.stat()
    content = path.read_bytes()
    path.write_bytes(bytes([content[0] ^ 1]) + content[1:])
    os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
    after = path.stat()
    assert (before.st_size, before.st_mtime_ns, before.st_ctime_ns,
            before.st_ino) == (after.st_size, after.st_mtime_ns,
                               after.st_ctime_ns, after.st_ino)


@pytest.mark.skipif(os.name != "nt", reason="Windows ctime permits restored-metadata edits")
@pytest.mark.parametrize("artifact", ["part", "output"])
def test_valid_same_metadata_change_between_first_plan_and_authorization_is_refused(
        tmp_path, monkeypatch, artifact):
    import tikrec.retention_execute as executor

    root, parts, _, config, _, audit, run = fixture(tmp_path)
    target = parts / "part-0001.flv" if artifact == "part" else root / "alpha.mp4"
    original_plan = executor._plan_retention_with_snapshot
    calls = 0

    def after_first_plan(*args, **kwargs):
        nonlocal calls
        result = original_plan(*args, **kwargs)
        calls += 1
        if calls == 1:
            if artifact == "part":
                before = target.stat()
                content = target.read_bytes()
                assert b"video" in content
                target.write_bytes(content.replace(b"video", b"wideo", 1))
                os.utime(target, ns=(before.st_atime_ns, before.st_mtime_ns))
                after = target.stat()
                assert (before.st_size, before.st_mtime_ns, before.st_ctime_ns,
                        before.st_ino) == (after.st_size, after.st_mtime_ns,
                                           after.st_ctime_ns, after.st_ino)
            else:
                _change_bytes(target)
            # Both changed files still pass structural and injected media checks.
            assert plan_retention(root, config.load(), clock=lambda: NOW,
                                  media_inspector=inspect)["sessions"][0][
                                      "classification"] == "eligible"
        return result

    monkeypatch.setattr(executor, "_plan_retention_with_snapshot", after_first_plan)
    with pytest.raises(ValueError, match="eligible file bytes changed"):
        run()
    assert calls == 1 and parts.exists() and (root / "alpha.mp4").exists()
    assert not audit.exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows ctime permits restored-metadata edits")
@pytest.mark.parametrize("artifact", ["part", "output"])
@pytest.mark.parametrize("stage", ["before_intent", "after_intent", "after_attempt"])
def test_restored_metadata_media_change_blocks_all_boundaries(
        tmp_path, monkeypatch, artifact, stage):
    import tikrec.retention_execute as executor
    from tikrec.retention_audit import RetentionAudit

    root, parts, _, config, _, audit, run = fixture(tmp_path)
    target = parts / "part-0001.flv" if artifact == "part" else root / "alpha.mp4"
    expected_output = (root / "alpha.mp4").read_bytes()

    def media_inspector(path):
        return MEDIA if path.read_bytes() == expected_output else None

    def mutate():
        _change_bytes(target)
        current = plan_retention(root, config.load(), clock=lambda: NOW,
                                 media_inspector=media_inspector)["sessions"][0]
        assert current["classification"] == "needs_attention"

    if stage == "before_intent":
        original = executor.check_policy
        calls = 0

        def after_plan(*args):
            nonlocal calls
            calls += 1
            if calls == 1:
                mutate()
            return original(*args)

        monkeypatch.setattr(executor, "check_policy", after_plan)
    elif stage == "after_attempt":
        original = RetentionAudit.append
        changed = False

        def after_attempt(self, event, operation_id, **fields):
            nonlocal changed
            original(self, event, operation_id, **fields)
            if event == "attempt" and not changed:
                changed = True
                mutate()

        monkeypatch.setattr(RetentionAudit, "append", after_attempt)
    callback = (lambda _path: mutate()) if stage == "after_intent" else None
    with pytest.raises(ValueError, match="byte proof"):
        run(media_inspector=media_inspector, before_mutation=callback)
    assert parts.exists() and (root / "alpha.mp4").exists()
    if stage == "before_intent":
        assert not audit.exists()
    else:
        assert events(audit)[-1]["event"] == "failed"
        assert not any(event["event"] == "deleted" for event in events(audit))


@pytest.mark.skipif(os.name != "nt", reason="Windows ctime permits restored-metadata edits")
@pytest.mark.parametrize("artifact", ["part", "output"])
def test_late_media_change_stops_after_prior_authorized_removals(
        tmp_path, artifact):
    root, parts, _, config, _, audit, run = fixture(tmp_path)
    if artifact == "part":
        from tests.test_writer import audio, audio_configuration, avc_configuration, video
        from tikrec.writer import write_parts
        import json
        write_parts([audio_configuration(90), avc_configuration(100, b"config"),
                     video(120, 1), audio(125)], parts, start_index=2)
        manifest = parts / "session.json"
        values = json.loads(manifest.read_text())
        values["part_count"] = 2
        manifest.write_text(json.dumps(values))
        target = parts / "part-0002.flv"
        change_at = 2
    else:
        target = root / "alpha.mp4"
        change_at = 3
    expected_output = (root / "alpha.mp4").read_bytes()

    def media_inspector(path):
        return MEDIA if path.read_bytes() == expected_output else None

    assert plan_retention(root, config.load(), clock=lambda: NOW,
                          media_inspector=media_inspector)["sessions"][0][
                              "classification"] == "eligible"
    calls = 0

    def late_change(_path: Path):
        nonlocal calls
        calls += 1
        if calls == change_at:
            _change_bytes(target)

    with pytest.raises(ValueError, match="byte proof"):
        run(media_inspector=media_inspector, before_mutation=late_change)
    assert calls == change_at and (root / "alpha.mp4").exists()
    assert events(audit)[-1]["event"] == "failed"
    assert [event["event"] for event in events(audit)].count("deleted") == change_at - 1
