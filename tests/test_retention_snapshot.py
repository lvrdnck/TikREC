"""Bounded claim snapshots must retain content identity across equal metadata."""

import json
import os

import pytest

from tests.test_retention_plan import session
from tikrec.retention_snapshot import capture_claim, capture_root


def change_during_closing_inventory(root, monkeypatch, *, scan, action):
    """Run a mutation inside the selected root iterdir generator's final step."""
    original = type(root).iterdir
    scans = 0

    def listing(path):
        nonlocal scans
        entries = original(path)
        if path != root:
            return entries
        scans += 1
        current = scans

        def observed():
            yield from entries
            if current == scan:
                action()

        return observed()

    monkeypatch.setattr(type(root), "iterdir", listing)
    return lambda: scans


@pytest.mark.parametrize("scan", [2, 4])
def test_claimant_created_inside_closing_inventory_invalidates_root(
        tmp_path, monkeypatch, scan):
    """A newly yielded omission must poison either planner root observation."""
    from tests.test_retention_plan import plan

    session(tmp_path, "alpha")
    scans = change_during_closing_inventory(
        tmp_path, monkeypatch, scan=scan,
        action=lambda: session(tmp_path, "late", creator="bravo"))
    results = plan(tmp_path, protected=("bravo",))
    assert scans() == 4
    assert all(item["classification"] != "eligible" for item in results)


def test_claimant_created_inside_capture_closing_inventory_is_unstable(
        tmp_path, monkeypatch):
    """The mutation occurs after old entries yield but before iterdir finishes."""
    session(tmp_path, "alpha")
    scans = change_during_closing_inventory(
        tmp_path, monkeypatch, scan=2,
        action=lambda: session(tmp_path, "late", creator="bravo"))
    assert not capture_root(tmp_path, capture_claim).stable
    assert scans() == 2


@pytest.mark.parametrize("action", ["remove", "replace"])
def test_child_change_inside_closing_enumeration_is_unstable(
        tmp_path, monkeypatch, action):
    """Closing child identity must match the claimant read earlier."""
    directory = session(tmp_path, "alpha")

    def change():
        directory.rename(tmp_path / "old")
        if action == "replace":
            session(tmp_path, "alpha", creator="bravo")

    change_during_closing_inventory(tmp_path, monkeypatch, scan=2, action=change)
    assert not capture_root(tmp_path, capture_claim).stable


def test_stable_root_inventory_remains_stable(tmp_path):
    session(tmp_path, "alpha")
    assert capture_root(tmp_path, capture_claim).stable


def test_unreadable_closing_inventory_is_unstable(tmp_path, monkeypatch):
    session(tmp_path, "alpha")

    def unreadable():
        raise OSError("closing inventory unreadable")

    change_during_closing_inventory(
        tmp_path, monkeypatch, scan=2, action=unreadable)
    assert not capture_root(tmp_path, capture_claim).stable


def test_root_capture_rejects_claimant_added_during_its_own_scan(tmp_path):
    """A single returned snapshot must represent a stable membership interval."""
    from tests.test_retention_plan import session

    session(tmp_path, "alpha")

    def changing(path, root):
        claim = capture_claim(path, root)
        session(root, "late", creator="bravo")
        return claim

    assert not capture_root(tmp_path, changing).stable


def test_root_capture_rejects_claimant_removed_during_scan(tmp_path):
    """An omitted former owner cannot be treated as a stable empty root."""
    directory = session(tmp_path, "alpha")

    def changing(path, root):
        claim = capture_claim(path, root)
        directory.rename(root / "removed")
        return claim

    assert not capture_root(tmp_path, changing).stable


def test_root_capture_rejects_child_replacement_during_scan(tmp_path, monkeypatch):
    """A same-name replacement must not inherit the former child's claim."""
    import tikrec.retention_snapshot as snapshot

    directory = session(tmp_path, "alpha")
    stamp = snapshot._stamp
    root_stamp = stamp(tmp_path)
    monkeypatch.setattr(snapshot, "_stamp",
                        lambda path: root_stamp if path == tmp_path else stamp(path))

    def changing(path, root):
        claim = capture_claim(path, root)
        directory.rename(root / "old")
        session(root, "alpha", creator="beta")
        return claim

    assert not capture_root(tmp_path, changing).stable


def test_root_capture_rejects_root_metadata_change_during_scan(tmp_path):
    """The root stamp brackets the entire claimant inspection."""
    session(tmp_path, "alpha")

    def changing(path, root):
        claim = capture_claim(path, root)
        before = root.stat()
        os.utime(root, ns=(before.st_atime_ns, before.st_mtime_ns + 1_000_000_000))
        return claim

    assert not capture_root(tmp_path, changing).stable


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
