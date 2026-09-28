"""Quarantine must never remove a post-check replacement as an authorized file."""

from pathlib import Path

import pytest

from tests.test_retention_execute import events, fixture


@pytest.mark.parametrize("kind", ["file", "directory"])
def test_replacement_after_final_check_is_quarantined_but_not_deleted(
        tmp_path, monkeypatch, kind):
    import tikrec.retention_mutation as mutation

    root, parts, _, _, _, audit, run = fixture(tmp_path)
    original = mutation.check_fingerprint
    saved = root / f"saved-{kind}"
    replaced = False

    def swap_after_check(scope, item, volume):
        nonlocal replaced
        result = original(scope, item, volume)
        if not replaced and item.kind == kind:
            replaced = True
            path = scope / item.relative_path
            path.rename(saved)
            if kind == "file":
                path.write_bytes(b"unapproved replacement")
            else:
                path.mkdir()
        return result

    monkeypatch.setattr(mutation, "check_fingerprint", swap_after_check)
    with pytest.raises(ValueError, match="quarantined artifact identity"):
        run()
    assert replaced and saved.exists() and (root / "alpha.mp4").exists()
    records = events(audit)
    assert records[-1]["event"] == "failed"
    assert not any(record["event"] == "completed" for record in records)
    attempted = records[-2]["path"]
    index = records[0]["order"].index(attempted)
    private = root / records[0]["quarantine_order"][index]
    assert private.exists()
    if kind == "file":
        assert private.read_bytes() == b"unapproved replacement"
    else:
        assert private.is_dir()


def test_failure_after_quarantine_leaves_auditable_nonresumable_artifact(
        tmp_path, monkeypatch):
    import tikrec.retention_execute as executor

    root, parts, _, _, _, audit, run = fixture(tmp_path)
    original = executor._sync_parent
    calls = 0

    def fail_first_sync(path: Path):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise OSError("injected quarantine sync failure")
        return original(path)

    monkeypatch.setattr(executor, "_sync_parent", fail_first_sync)
    with pytest.raises(OSError, match="quarantine sync"):
        run()
    records = events(audit)
    assert [event["event"] for event in records] == ["intent", "attempt", "failed"]
    private = root / records[0]["quarantine_order"][0]
    assert private.exists() and not (parts / "part-0001.flv").exists()
    monkeypatch.setattr(executor, "_sync_parent", original)
    with pytest.raises(ValueError, match="eligible"):
        run()
    assert (root / "alpha.mp4").exists()
