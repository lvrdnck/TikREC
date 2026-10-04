"""Bind real native inventory, optional diagnostics and empty/failure dispositions."""

import json
import os
from pathlib import Path

import pytest

from tests.capture_handoff_helpers import authority, local_media, manifest, observations, reserve
from tikrec.capture_handoff import CaptureHandoffError

pytestmark = pytest.mark.skipif(os.name != "nt", reason="requires native Windows inventory proof")


def test_actual_raw_arrival_connection_inventory_and_hashes(tmp_path):
    import hashlib
    data = local_media(tmp_path / "fixture.flv")
    with authority(tmp_path) as owner:
        bridge = reserve(owner)
        bridge.run(**observations(data))
        seal = owner.journal.session(bridge.intent.session_id)["seal"]
        assert [a["role"] for a in seal["artifacts"]] == ["flv", "raw", "arrivals", "connections", "manifest"]
        for artifact in seal["artifacts"]:
            path = Path(bridge.intent.parts_path, artifact["identity"]["components"][-1])
            assert artifact["size"] == path.stat().st_size
            assert artifact["identity"]["volume"].startswith("volume{")
            assert len(artifact["stamp"].split(":")) == 4
            if artifact["role"] in {"manifest", "connections"}:
                assert artifact["control_hash"] == hashlib.sha256(path.read_bytes()).hexdigest()
        log = Path(bridge.intent.parts_path, "connections.jsonl")
        connection = next(json.loads(v) for v in log.read_text().splitlines() if "raw_copy" in v)
        assert connection["raw_copy"] == "connection-0001.raw"
        assert connection["raw_arrivals"] == "connection-0001.arrivals.jsonl"
        arrivals = [json.loads(v) for v in Path(bridge.intent.parts_path, connection["raw_arrivals"]).read_text().splitlines()]
        assert sum(v.get("count", 0) for v in arrivals) == len(data)


def test_optional_raw_write_failure_keeps_real_remainders_without_claiming_success(tmp_path):
    data = local_media(tmp_path / "fixture.flv")
    with authority(tmp_path) as owner:
        bridge = reserve(owner)
        normal = observations(data)
        original = normal["raw_tag_source"]
        def source(url, raw):
            actual = raw.raw._handle
            class Failing:
                def write(self, _):
                    raise OSError("optional raw disk error")
                def close(self):
                    actual.close()
            raw.raw._handle = Failing()
            yield from original(url, raw)
        normal["raw_tag_source"] = source
        result = bridge.run(**normal)
        assert result.phase == "queued"
        seal = owner.journal.session(bridge.intent.session_id)["seal"]
        assert seal["raw_copy"] and {"raw_warning", "raw_remainder_retained"} <= set(seal["warnings"])
        assert any(a["role"] == "raw" for a in seal["artifacts"])
        records = [json.loads(v) for v in Path(bridge.intent.parts_path, "connections.jsonl").read_text().splitlines()]
        assert next(v for v in records if "outcome" in v)["raw_copy"] is None


@pytest.mark.parametrize("ambiguous", [False, True])
def test_proved_zero_media_retains_evidence_but_discarded_tags_are_ambiguous(tmp_path, ambiguous):
    with authority(tmp_path) as owner:
        bridge = reserve(owner, raw=False)
        opts = observations(b"")
        if ambiguous:
            from tests.test_live import stream
            opts["tag_source"] = lambda _: iter(stream()[:1])
            with pytest.raises(CaptureHandoffError):
                bridge.run(**opts)
            row = owner.journal.session(bridge.intent.session_id)
            assert row["phase"] == "closing" and row["seal"] is None and row["task"] is None
        else:
            opts["tag_source"] = lambda _: iter(())
            assert bridge.run(**opts).phase == "no_assembly"
            row = owner.journal.session(bridge.intent.session_id)
            assert row["seal"]["disposition"] == "empty" and row["task"] is None
            assert owner.journal.status()["units"][0]["kind"] == "evidence"
            assert len(row["artifacts"]) == 2 and row["rooms"] == ["123"]
            assert owner.inspect(bridge.intent.session_id)["phase"] == "no_assembly"


@pytest.mark.parametrize("tamper", ["manifest", "connections", "partial"])
def test_control_binding_or_unexplained_partial_never_gets_a_seal(tmp_path, tamper):
    data = local_media(tmp_path / "fixture.flv")
    with authority(tmp_path) as owner:
        bridge = reserve(owner)
        def fault(boundary):
            if boundary != "before_inventory":
                return
            parts = Path(bridge.intent.parts_path)
            if tamper == "manifest":
                values = manifest(bridge)
                values["session_id"] = "incorrect"
                (parts / "session.json").write_text(json.dumps(values))
            elif tamper == "connections":
                path = parts / "connections.jsonl"
                path.write_text(path.read_text().replace('"connection-0001.raw"', '"connection-0009.raw"'))
            else:
                (parts / ".part-0002.flv.partial").write_bytes(b"recovery evidence")
        bridge._fault = fault
        with pytest.raises(CaptureHandoffError):
            bridge.run(**observations(data))
        row = owner.journal.session(bridge.intent.session_id)
        assert row["phase"] == "closing" and row["seal"] is None and row["task"] is None


def test_native_diagnostic_inventory_orders_numeric_connections_beyond_four_digits(tmp_path):
    from tikrec.capture_handoff_inventory import _inventory_order
    from tikrec.capture_handoff_native import NativeHandle
    from tikrec.session_journal_types import ClosedArtifact
    names = ["connection-10000.arrivals.jsonl", "connection-10000.raw",
             "connection-9999.arrivals.jsonl", "connection-9999.raw"]
    artifacts = []
    for name in names:
        path = tmp_path / name
        path.write_bytes(b"fixture")
        with NativeHandle(path) as held:
            artifacts.append(ClosedArtifact(held.identity, "raw" if name.endswith(".raw") else "arrivals",
                                            held.size, held.stamp))
    assert [a.identity.components[-1] for a in sorted(artifacts, key=_inventory_order)] == [
        "connection-9999.raw", "connection-9999.arrivals.jsonl",
        "connection-10000.raw", "connection-10000.arrivals.jsonl"]
