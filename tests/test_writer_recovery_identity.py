"""Recovery identity comparisons retain replacement and metadata stability checks."""

import hashlib
import os
from pathlib import Path
import stat
from types import SimpleNamespace

import pytest

from tests.test_writer_recovery_evidence import after_first_source_read
import tikrec.writer_recovery_evidence as evidence


def changed_metadata(details, field):
    """Copy an observed identity with one changed field and otherwise equal bytes."""
    fields = ("st_mode", "st_size", "st_dev", "st_ino", "st_mtime_ns",
              "st_ctime_ns", "st_nlink", "st_file_attributes")
    values = {name: getattr(details, name, 0) for name in fields}
    # Change permissions without changing the regular-file classification.
    values[field] ^= stat.S_IXUSR if field == "st_mode" else 1
    return SimpleNamespace(**values)


@pytest.mark.parametrize("platform", ["nt", "posix"])
@pytest.mark.parametrize("field", [
    "st_mode", "st_size", "st_dev", "st_ino", "st_mtime_ns", "st_ctime_ns",
    "st_nlink", "st_file_attributes",
])
def test_opening_path_handle_comparison_omits_only_windows_ctime(
        tmp_path, monkeypatch, platform, field):
    """Only Windows cross-API ctime disagreement can admit otherwise equal files."""
    source, recovered = tmp_path / "source", tmp_path / "recovered"
    source.write_bytes(b"identical")
    recovered.write_bytes(b"identical")
    original_lstat = Path.lstat
    original_fstat = os.fstat
    path_ctimes = {path.stat().st_ino: path.stat().st_ctime_ns
                  for path in (source, recovered)}

    def path_metadata(path):
        details = original_lstat(path)
        return changed_metadata(details, field) if path == source else details

    def handle_metadata(descriptor):
        details = original_fstat(descriptor)
        # Normalize native ctime solely to exercise both platform policies offline.
        values = changed_metadata(details, "st_ctime_ns")
        values.st_ctime_ns = path_ctimes[details.st_ino]
        return values

    # Replace only this module's OS reference; pathlib keeps the host platform.
    monkeypatch.setattr(evidence, "os", SimpleNamespace(name=platform, fstat=handle_metadata))
    monkeypatch.setattr(Path, "lstat", path_metadata)
    assert evidence.prove_recovery_bytes(
        source, recovered, 9, 9, hashlib.sha256(b"identical").hexdigest()
    ) is (platform == "nt" and field == "st_ctime_ns")


@pytest.mark.parametrize("api", ["path", "handle"])
@pytest.mark.parametrize("artifact", ["source", "recovered"])
def test_windows_proof_rejects_ctime_drift_within_each_api(
        tmp_path, monkeypatch, api, artifact):
    """Ignoring cross-API ctime must not ignore a path or handle's later change."""
    source, recovered = tmp_path / "source", tmp_path / "recovered"
    source.write_bytes(b"identical")
    recovered.write_bytes(b"identical")
    target = source if artifact == "source" else recovered
    target_inode = target.stat().st_ino
    original_lstat, original_fstat = Path.lstat, os.fstat
    drift = False

    def path_metadata(path):
        details = original_lstat(path)
        if drift and api == "path" and path == target:
            return changed_metadata(details, "st_ctime_ns")
        return details

    def handle_metadata(descriptor):
        details = original_fstat(descriptor)
        if drift and api == "handle" and details.st_ino == target_inode:
            return changed_metadata(details, "st_ctime_ns")
        return details

    def change():
        nonlocal drift
        drift = True

    monkeypatch.setattr(evidence, "os", SimpleNamespace(name="nt", fstat=handle_metadata))
    monkeypatch.setattr(Path, "lstat", path_metadata)
    fired = after_first_source_read(monkeypatch, source, change)
    assert not evidence.prove_recovery_bytes(
        source, recovered, 9, 9, hashlib.sha256(b"identical").hexdigest())
    assert fired() and source.read_bytes() == recovered.read_bytes() == b"identical"
