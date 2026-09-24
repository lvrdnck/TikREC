"""Writer recovery prefix evidence must prove every recorded byte."""

import json

import pytest

from tests.test_writer_recovery import crashed_session, evidence_path, reconciler
from tikrec.session_parts import RetainedParts
from tikrec.writer_recovery_evidence import same_prefix, validate_recorded_evidence


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
    import tikrec.writer_recovery_evidence as module

    store, _, manifest, partial = crashed_session(tmp_path)
    assert reconciler(store).reconcile().outcome == "resume"
    part = partial.parent / "part-0001.flv"
    evidence = evidence_path(partial.parent)
    records = json.loads(manifest.path.read_text())["writer_recoveries"]
    original = module.same_prefix
    changed = False

    def shorten_both(left, right, count):
        nonlocal changed
        changed = True
        left.write_bytes(b"")
        right.write_bytes(b"")
        return original(left, right, count)

    monkeypatch.setattr(module, "same_prefix", shorten_both)
    with pytest.raises(ValueError, match="byte evidence"):
        validate_recorded_evidence(
            partial.parent, RetainedParts((part,), 2), records, (evidence,))
    assert changed
