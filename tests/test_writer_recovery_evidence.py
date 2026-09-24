"""Writer recovery prefix evidence must prove every recorded byte."""

import json
import hashlib
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.test_writer import video
from tests.test_writer_recovery import (crashed_session, evidence_path, media_bytes,
                                        reconciler)
from tikrec.session_parts import RetainedParts
from tikrec.writer_recovery_evidence import (prove_recovery_bytes, same_prefix,
                                             validate_recorded_evidence)


def after_first_source_read(monkeypatch, source, action, *, when=lambda: True):
    """Inject a file change after the reader obtained old bytes, only once."""
    original = Path.open
    fired = False

    class ObservedFile:
        def __init__(self, handle):
            self.handle = handle

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return self.handle.__exit__(*args)

        def __getattr__(self, name):
            return getattr(self.handle, name)

        def read(self, size=-1):
            nonlocal fired
            chunk = self.handle.read(size)
            if chunk and not fired and when():
                fired = True
                action()
            return chunk

    def opening(path, *args, **kwargs):
        handle = original(path, *args, **kwargs)
        if path == source and args and args[0] == "rb":
            return ObservedFile(handle)
        return handle

    monkeypatch.setattr(Path, "open", opening)
    return lambda: fired


def torn_recovery(tmp_path):
    """Provide a valid 71-byte recovered prefix and an evidence-only tail."""
    clean = media_bytes(tmp_path)
    store, _, manifest, partial = crashed_session(
        tmp_path, content=clean + video(160, 2).encoded()[:-3])
    return store, manifest, partial


@pytest.mark.parametrize("mutation", ["prefix", "tail"])
def test_final_manifest_guard_binds_hash_and_prefix_to_one_observation(
        tmp_path, monkeypatch, mutation):
    """Old-hash/new-prefix or old-hash/new-tail cannot publish a recovery."""
    store, manifest, partial = torn_recovery(tmp_path)
    source = evidence_path(partial.parent)
    part = partial.parent / "part-0001.flv"
    committed = manifest.path.read_bytes()
    temporary = manifest.path.with_name(f".{manifest.path.name}.partial")
    inventory_at_guard = None

    def change():
        nonlocal inventory_at_guard
        inventory_at_guard = {path.name for path in partial.parent.iterdir()}
        data = bytearray(source.read_bytes())
        offset = 20 if mutation == "prefix" else len(part.read_bytes()) + 1
        data[offset] ^= 1
        source.write_bytes(data)
        if mutation == "prefix":
            part.write_bytes(data[:part.stat().st_size])

    fired = after_first_source_read(
        monkeypatch, source, change, when=temporary.exists)
    result = reconciler(store).reconcile()
    assert fired() and result.outcome == "failed"
    assert inventory_at_guard - {temporary.name} == {
        path.name for path in partial.parent.iterdir()}
    assert not temporary.exists()
    assert source.exists() and part.exists()
    assert manifest.path.read_bytes() == committed
    assert b'"writer_recoveries"' not in committed


def test_persisted_record_rejects_old_hash_with_new_matching_prefix(
        tmp_path, monkeypatch):
    """A recorded source hash cannot be paired with a later matching prefix."""
    store, manifest, partial = torn_recovery(tmp_path)
    assert reconciler(store).reconcile().outcome == "resume"
    source = evidence_path(partial.parent)
    part = partial.parent / "part-0001.flv"
    records = json.loads(manifest.path.read_text())["writer_recoveries"]

    def change():
        data = bytearray(source.read_bytes())
        data[20] ^= 1
        source.write_bytes(data)
        part.write_bytes(data[:part.stat().st_size])

    fired = after_first_source_read(monkeypatch, source, change)
    with pytest.raises(ValueError, match="byte evidence"):
        validate_recorded_evidence(
            partial.parent, RetainedParts((part,), 2), records, (source,))
    assert fired()


@pytest.mark.parametrize("replaced", ["source", "recovered"])
def test_final_manifest_guard_rejects_identity_drift_during_proof(
        tmp_path, monkeypatch, replaced):
    """Injected path identity drift must not inherit the opened identity."""
    store, manifest, partial = torn_recovery(tmp_path)
    source = evidence_path(partial.parent)
    part = partial.parent / "part-0001.flv"
    target = source if replaced == "source" else part
    committed = manifest.path.read_bytes()
    temporary = manifest.path.with_name(f".{manifest.path.name}.partial")
    original_lstat = Path.lstat
    drift = False

    def changed_identity(path):
        details = original_lstat(path)
        if path != target or not drift:
            return details
        values = {name: getattr(details, name) for name in
                  ("st_mode", "st_size", "st_mtime_ns", "st_ctime_ns",
                   "st_dev", "st_ino", "st_nlink") if hasattr(details, name)}
        values["st_ino"] += 1
        values["st_file_attributes"] = getattr(details, "st_file_attributes", 0)
        return SimpleNamespace(**values)

    def replace_identity():
        nonlocal drift
        drift = True

    # Simulate a same-content replacement because Windows forbids renaming an open file.
    monkeypatch.setattr(Path, "lstat", changed_identity)
    fired = after_first_source_read(
        monkeypatch, source, replace_identity, when=temporary.exists)
    result = reconciler(store).reconcile()
    assert fired() and result.outcome == "failed"
    assert manifest.path.read_bytes() == committed
    assert not temporary.exists()


@pytest.mark.skipif(os.name == "nt", reason="Windows cannot replace an open file")
@pytest.mark.parametrize("replaced", ["source", "recovered"])
def test_actual_same_byte_replacement_during_proof_is_rejected(
        tmp_path, monkeypatch, replaced):
    """On POSIX, path replacement during an opened proof must fail closed."""
    store, manifest, partial = torn_recovery(tmp_path)
    source = evidence_path(partial.parent)
    part = partial.parent / "part-0001.flv"
    target = source if replaced == "source" else part
    replacement = tmp_path / f"replacement-{replaced}"
    temporary = manifest.path.with_name(f".{manifest.path.name}.partial")
    committed = manifest.path.read_bytes()

    def replace_path():
        replacement.write_bytes(target.read_bytes())
        os.replace(replacement, target)

    fired = after_first_source_read(
        monkeypatch, source, replace_path, when=temporary.exists)
    result = reconciler(store).reconcile()
    assert fired() and result.outcome == "failed"
    assert manifest.path.read_bytes() == committed
    assert not temporary.exists()
    assert source.exists() and part.exists()


@pytest.mark.parametrize("redirected", ["source", "recovered"])
def test_coherent_proof_rejects_reparse_artifact(tmp_path, monkeypatch, redirected):
    """Regular-looking Windows reparse artifacts are not byte-proof inputs."""
    source, recovered = tmp_path / "source", tmp_path / "recovered"
    source.write_bytes(b"identical")
    recovered.write_bytes(b"identical")
    target = source if redirected == "source" else recovered
    original = Path.lstat

    def reparse(path):
        details = original(path)
        if path != target:
            return details
        values = {name: getattr(details, name) for name in
                  ("st_mode", "st_size", "st_mtime_ns", "st_ctime_ns",
                   "st_dev", "st_ino", "st_nlink") if hasattr(details, name)}
        values["st_file_attributes"] = 0x400
        return SimpleNamespace(**values)

    monkeypatch.setattr(Path, "lstat", reparse)
    assert not prove_recovery_bytes(
        source, recovered, 9, 9, hashlib.sha256(b"identical").hexdigest())


@pytest.mark.parametrize("source,recovered,count,expected", [
    (b"", b"", 0, True),
    (b"matching-tail", b"matching-other", 8, True),
    (b"matching", b"matXhing", 8, False),
    (b"short", b"shorter than short", 8, False),
    (b"shorter than short", b"short", 8, False),
    (b"short", b"short", 8, False),
    (b"same", b"same", 8, False),
    (b"a" * (64 * 1024 + 17), b"a" * (64 * 1024 + 17), 64 * 1024 + 17, True),
], ids=["zero", "identical", "different", "source-eof", "recovered-eof",
        "both-eof", "equal-short-read", "multiple-chunks"])
def test_exact_prefix_requires_every_requested_byte(
        tmp_path, source, recovered, count, expected):
    left, right = tmp_path / "source", tmp_path / "recovered"
    left.write_bytes(source)
    right.write_bytes(recovered)
    assert same_prefix(left, right, count) is expected


def test_persisted_recovery_record_rejects_equal_eof_during_prefix_proof(
        tmp_path, monkeypatch):
    """Earlier size/hash checks cannot authorize a later equal EOF."""
    store, _, manifest, partial = crashed_session(tmp_path)
    assert reconciler(store).reconcile().outcome == "resume"
    part = partial.parent / "part-0001.flv"
    evidence = evidence_path(partial.parent)
    records = json.loads(manifest.path.read_text())["writer_recoveries"]
    def shorten_both():
        evidence.write_bytes(b"")
        part.write_bytes(b"")

    fired = after_first_source_read(monkeypatch, evidence, shorten_both)
    with pytest.raises(ValueError, match="byte evidence"):
        validate_recorded_evidence(
            partial.parent, RetainedParts((part,), 2), records, (evidence,))
    assert fired()
