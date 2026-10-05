"""Bounded packet framing shares accepted DTS semantics and proves final EOF."""

import json
from types import SimpleNamespace

import pytest

from tikrec.candidate_validation_diagnostics import ValidationDiagnostics
from tikrec.part_validation import verify_packet_dts


def collect(data, stderr=b""):
    """Replay bounded chunks with exact native prefix/drop/EOF evidence."""
    collector = ValidationDiagnostics(2)
    for name, value in (("stdout", data), ("stderr", stderr)):
        for offset in range(0, len(value), 8192):
            collector.observe(name, value[offset:offset + 8192])
    collector.finish(SimpleNamespace(stream_status=("complete", "complete"), stdout=data[:16384],
        stderr=stderr[:16384], truncated=(max(0, len(data) - 16384), max(0, len(stderr) - 16384))))
    return collector


@pytest.mark.parametrize("values", [[0, 1, 2], [2, 1, 3], [0, 2, 1], [0, 0], [1, 2, 2]])
def test_streamed_packet_findings_match_accepted_dts_semantics(values):
    data = "\n".join(f"stream_index=0|dts={dts}" for dts in values).encode()
    collector = collect(data)
    document = json.dumps({"packets": [{"stream_index": 0, "dts": dts} for dts in values]})
    if len(set(values)) != len(values):
        with pytest.raises(ValueError):
            verify_packet_dts(document)
        assert collector.packet_problems
    else:
        assert collector.packet_warnings == verify_packet_dts(document)
        assert not collector.packet_problems


def test_many_packets_are_streamed_with_bounded_state_and_unterminated_tail():
    data = "\n".join(f"stream_index=0|dts={index}" for index in range(10000)).encode()
    collector = collect(data)
    assert collector.packet_count == 10000 and len(collector.previous) == 1
    assert not collector.packet_line and not collector.packet_problems and collector.complete


@pytest.mark.parametrize("data", [b"", b"stream_index=0|dts=N/A", b"malformed packet"])
def test_missing_or_invalid_packet_evidence_cannot_pass(data):
    assert collect(data).packet_problems


def test_oversized_packet_line_and_invalid_utf8_are_explicit_failures():
    with pytest.raises(Exception, match="bounded"):
        collect(b"x" * 65537)
    with pytest.raises(UnicodeDecodeError):
        collect(b"\xff")


def test_first_diagnostic_framing_failure_is_preserved_explicitly():
    with pytest.raises(ValueError, match="diagnostic UTF-8 could not be decoded completely"):
        collect(b"stream_index=0|dts=0", b"\xff")
