"""Unknown partial raw acquisitions cannot masquerade as zero native ownership."""

import hashlib
import os
from pathlib import Path

import pytest

from tikrec.capture_input_owners import CaptureInputOwners
from tikrec.source import RawCopy

pytestmark = pytest.mark.skipif(os.name != 'nt', reason='original Windows raw close references')


def test_suppressed_raw_open_failure_retains_partial_owner_and_never_proves_empty(tmp_path, monkeypatch):
    """A native stream acquired before a reported open failure stays explicitly uncertain."""
    target = tmp_path / 'partial.raw'
    owner, originals, warnings = CaptureInputOwners(), [], []
    primary = OSError('generated unacknowledged raw open')
    opening = Path.open
    def failed(path, *args, **options):
        if path != target or not args or args[0] != 'xb':
            return opening(path, *args, **options)
        raw = opening(path, *args, **options)
        originals.append(raw)
        raw.write(b'original generated evidence')
        raw.flush()
        primary.capture_partial_stream = raw  # Named fixture retains the exact original owner.
        raise primary
    monkeypatch.setattr(Path, 'open', failed)
    try:
        raw = RawCopy(target, warnings.append, _open=owner.open)
        assert raw._handle is None and warnings
        assert not originals[0].closed
        before = hashlib.sha256(target.read_bytes()).hexdigest()
        assert not owner.retired() and not owner.retire()
        assert any(e is primary for e in owner.errors)
        assert hashlib.sha256(target.read_bytes()).hexdigest() == before
    finally:
        # Independent disposable partial-owner cleanup is never positive product retirement.
        for stream in originals:
            stream.close()


def test_guard_setup_failure_keeps_original_stream_reference_and_secondary_error(tmp_path, monkeypatch):
    """RawCopy warnings cannot discard guard-constructor failure identity or native references."""
    from tikrec.release_recovery_handles import NativeCloseGuard
    owner, warnings = CaptureInputOwners(), []
    primary, secondary = OSError('generated guard setup failure'), OSError('secondary guard fault')
    primary.capture_cleanup_errors = [secondary]
    constructing = NativeCloseGuard.__init__
    def failed(guard, *args, **options):
        constructing(guard, *args, **options)
        raise primary
    monkeypatch.setattr(NativeCloseGuard, '__init__', failed)
    try:
        raw = RawCopy(tmp_path / 'guard.raw', warnings.append, _open=owner.open)
        assert raw._handle is None and warnings
        assert owner.streams and owner.native_close_guards[0].retained
        assert not owner.retired() and not owner.retire()
        assert any(e is primary for e in owner.errors) and any(e is secondary for e in owner.errors)
    finally:
        # Exact registered originals, not reopened paths or stale numeric descriptors.
        for entry, guard in zip(owner.streams, owner.native_close_guards):
            guard.close(entry['raw'].close)
            assert not guard.retained and entry['raw'].closed
