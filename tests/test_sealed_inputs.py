"""Addressed H authority, inventory, revalidation and independent lifecycle proofs."""

import json
import os
from pathlib import Path

import pytest

from tests.capture_handoff_helpers import authority, observations, reserve
from tests.sealed_input_helpers import acquire, hashes, restore_stamp, sealed

pytestmark = pytest.mark.skipif(os.name != "nt", reason="native Windows read protection")


def test_complete_real_inventory_is_read_only_and_lease_scoped(sealed):
    owner, bridge, row = sealed
    before, status = hashes(owner.root.parent), owner.journal.status()
    with acquire(sealed) as guard:
        evidence = guard.revalidate()
        assert [a.role for a in evidence.seal.artifacts] == [
            "flv", "raw", "arrivals", "connections", "manifest"]
        assert evidence.session_id == bridge.intent.session_id
        assert evidence.revision == row["revision"]
        assert evidence.seal_hash == row["seal_hash"]
        assert len(evidence.flv_inputs) == 1 and len(guard.handles) == 9
        assert evidence.seal.warnings == ()
        assert owner.journal.status() == status
    assert guard.closed and not guard.retained
    with pytest.raises(Exception, match="closed"):
        guard.revalidate()
    assert hashes(owner.root.parent) == before
    assert owner.journal.session(bridge.intent.session_id) == row
    assert not Path(bridge.intent.output_path).exists()


@pytest.mark.parametrize("change", ["remove", "add", "partial", "media", "raw", "arrivals",
                                   "manifest_hash", "connections_hash", "marker_missing",
                                   "marker_invalid", "marker_empty", "marker_revision", "marker_seal",
                                   "marker_operation", "marker_catalog", "marker_extra", "marker_raw_type"])
def test_tampering_refuses_without_repair_or_journal_changes(sealed, change):
    owner, bridge, row = sealed
    parts = Path(bridge.intent.parts_path)
    if change == "remove":
        (parts / "part-0001.flv").unlink()
    elif change in {"add", "partial"}:
        (parts / ("part-0002.flv" if change == "add" else ".part-0002.flv.partial")).write_bytes(b"extra")
    elif change in {"media", "raw", "arrivals"}:
        name = {"media": "part-0001.flv", "raw": "connection-0001.raw",
                "arrivals": "connection-0001.arrivals.jsonl"}[change]
        with (parts / name).open("ab") as handle:
            handle.write(b"changed")
    elif change.endswith("_hash"):
        path = parts / ("session.json" if change.startswith("manifest") else "connections.jsonl")
        info, data = path.stat(), path.read_bytes()
        path.write_bytes(b" " + data[1:])
        assert path.stat().st_size == info.st_size
        restore_stamp(path, info)
    else:
        marker = parts / "finalization-owner.json"
        if change == "marker_missing":
            marker.unlink()
        else:
            values = json.loads(marker.read_bytes())
            key, value = {"marker_invalid": ("disposition", "invalid"),
                          "marker_empty": ("disposition", "empty"),
                          "marker_revision": ("revision", 99),
                          "marker_seal": ("seal_hash", "0" * 64),
                          "marker_operation": ("operation", "00000000-0000-0000-0000-000000000001"),
                          "marker_catalog": ("catalog_id", "00000000-0000-0000-0000-000000000001"),
                          "marker_extra": ("unexpected", True),
                          "marker_raw_type": ("raw_copy", 1)}[change]
            values[key] = value
            marker.write_text(json.dumps(values))
    before, status = hashes(owner.root.parent), owner.journal.status()
    with pytest.raises(Exception) as failure:
        acquire(sealed)
    assert failure.value.guard.closed and not failure.value.guard.retained
    assert hashes(owner.root.parent) == before
    assert owner.journal.status() == status
    assert owner.journal.session(bridge.intent.session_id) == row


@pytest.mark.parametrize("binding", ["revision", "seal", "session", "empty", "pre_h"])
def test_only_explicit_committed_assembly_binding_is_admitted(tmp_path, binding):
    from tikrec.sealed_inputs import acquire_sealed_inputs
    with authority(tmp_path) as owner:
        bridge = reserve(owner, raw=False)
        if binding == "empty":
            options = observations(b"")
            options["tag_source"] = lambda _: iter(())
            bridge.run(**options)
        row = owner.journal.session(bridge.intent.session_id)
        with pytest.raises(Exception):
            acquire_sealed_inputs(owner, "00000000-0000-0000-0000-000000000001"
                                 if binding == "session" else bridge.intent.session_id,
                                 expected_revision=99 if binding == "revision" else row["revision"],
                                 expected_seal_hash=row["seal_hash"] or "0" * 64)


def test_disjoint_capture_and_catalog_mutations_do_not_invalidate_guard(sealed):
    owner, bridge, row = sealed
    from tikrec.lifecycle_lock import LifecycleBusy, acquire_lifecycle
    with acquire(sealed) as guard:
        with pytest.raises(LifecycleBusy):
            acquire_lifecycle(owner.root, "retention")
        other = reserve(owner, name="other", room="456", creator="other")
        other.run(**observations((owner.root.parent / "source.flv").read_bytes(), room="456"))
        assert guard.revalidate().revision == row["revision"]
        assert len(owner.journal.status()["units"]) == 2
        assert owner.journal.session(bridge.intent.session_id) == row
    with acquire_lifecycle(owner.root, "retention"):
        pass


def test_filesystem_barrier_does_not_hold_authority_lock(sealed):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    owner, _, _ = sealed
    entered, release = Event(), Event()
    def fault(boundary):
        if boundary == "before_inventory":
            entered.set()
            assert release.wait(10)
    with ThreadPoolExecutor() as pool:
        pending = pool.submit(acquire, sealed, fault=fault)
        try:
            assert entered.wait(10)
            other = pool.submit(reserve, owner, name="parallel", room="456")
            assert other.result(timeout=5).intent.expected_room == "456"
        finally:
            release.set()
        with pending.result(timeout=10) as guard:
            guard.revalidate()


def test_target_transition_and_closed_authority_are_stale(sealed):
    owner, bridge, row = sealed
    from tikrec.capture_handoff_authority import operation_id
    with acquire(sealed) as guard:
        owner.journal.claim_next(operation_id(), operation_id())
        with pytest.raises(Exception):
            guard.revalidate()
    owner.close()
    with pytest.raises(Exception):
        acquire(sealed)


@pytest.mark.parametrize("binding", ["revision", "seal", "unknown", "catalog", "missing_journal"])
def test_addressed_binding_refusal_preserves_actual_committed_owner(sealed, binding):
    from tikrec.sealed_inputs import acquire_sealed_inputs
    owner, bridge, row = sealed
    status, before = owner.journal.status(), hashes(owner.root.parent)
    catalog, path = owner.journal.catalog_id, owner.journal.path
    if binding == "catalog":
        owner.journal.catalog_id = "00000000-0000-0000-0000-000000000001"
    elif binding == "missing_journal":
        owner.journal.path = path.with_name("missing.sqlite3")
    try:
        with pytest.raises(Exception) as failure:
            acquire_sealed_inputs(owner, "00000000-0000-0000-0000-000000000001"
                if binding == "unknown" else bridge.intent.session_id,
                expected_revision=row["revision"] + (binding == "revision"),
                expected_seal_hash="0" * 64 if binding == "seal" else row["seal_hash"])
        assert not failure.value.guard.retained
    finally:
        owner.journal.catalog_id, owner.journal.path = catalog, path
    assert owner.journal.status() == status and hashes(owner.root.parent) == before
    assert owner.journal.session(bridge.intent.session_id) == row


def test_optional_raw_warning_remnants_are_held_without_upgrading_proof(tmp_path):
    from tests.capture_handoff_helpers import local_media
    data = local_media(tmp_path / "source.flv")
    with authority(tmp_path) as owner:
        bridge = reserve(owner)
        options = observations(data)
        normal = options["raw_tag_source"]
        def source(url, raw):
            actual = raw.raw._handle
            class Failing:
                def write(self, _):
                    raise OSError("optional raw failed")
                def close(self):
                    actual.close()
            raw.raw._handle = Failing()
            yield from normal(url, raw)
        options["raw_tag_source"] = source
        bridge.run(**options)
        row = owner.journal.session(bridge.intent.session_id)
        before = hashes(owner.root.parent)
        with acquire((owner, bridge, row)) as guard:
            evidence = guard.revalidate()
            assert {"raw_warning", "raw_remainder_retained"} <= set(evidence.seal.warnings)
            assert any(a.role == "raw" and a.size == 0 for a in evidence.seal.artifacts)
        assert hashes(owner.root.parent) == before
