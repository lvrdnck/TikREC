"""Actual committed capture fixtures for disposable sealed-input protection tests."""

import hashlib
import os
from pathlib import Path

import pytest

from tests.capture_handoff_helpers import authority, local_media, observations, reserve


@pytest.fixture
def sealed(tmp_path):
    """Hold a real authority around an H-committed raw-enabled generated capture."""
    data = local_media(tmp_path / "source.flv")
    with authority(tmp_path) as owner:
        bridge = reserve(owner)
        assert bridge.run(**observations(data)).phase == "queued"
        row = owner.journal.session(bridge.intent.session_id)
        yield owner, bridge, row


def acquire(fixture, **options):
    """Address the exact revision and seal, never discover a pending session."""
    from tikrec.sealed_inputs import acquire_sealed_inputs
    owner, bridge, row = fixture
    return acquire_sealed_inputs(owner, bridge.intent.session_id,
                                 expected_revision=row["revision"],
                                 expected_seal_hash=row["seal_hash"], **options)


def hashes(root):
    """Hash every fixture byte outside production; this is not the guard's proof."""
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in Path(root).rglob("*") if p.is_file() and p.name != ".tikrec-lifecycle.lock"}


def restore_stamp(path, details):
    """Allow tests to isolate control-hash proof from native length/write stamps."""
    os.utime(path, ns=(details.st_atime_ns, details.st_mtime_ns))
