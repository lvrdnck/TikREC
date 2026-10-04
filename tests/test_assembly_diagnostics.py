"""Bounded incremental diagnostics, independently of prefix retention."""

import pytest

from tikrec.assembly_diagnostics import AssemblyDiagnostics
from tikrec.owned_process_types import ProcessEvidence


def finish(parser, stdout=b"", stderr=b"", status=("complete", "complete")):
    evidence = ProcessEvidence("session", "attempt", "confirmed_exited", None, 0, 0,
                               stdout[:2], stderr[:2], (max(0, len(stdout)-2), max(0, len(stderr)-2)),
                               False, None, (), stream_status=status)
    parser.finish(evidence)
    return evidence


def test_split_utf8_and_crlf_final_line_are_observed_once():
    lines = []
    parser = AssemblyDiagnostics(decode=True, progress=lines.append)
    data = "warning café\r\n[h264 @ 0x1] corrupt slice".encode()
    for byte in data:
        parser.observe("stderr", bytes([byte]))
    evidence = finish(parser, stderr=data)
    parser.finish(evidence)
    assert parser.complete and parser.input_health()["status"] == "degraded"
    assert lines == ["ffmpeg: warning café", "ffmpeg: [h264 @ 0x1] corrupt slice"]


@pytest.mark.parametrize("data", [b"x" * 70000, b"invalid\xff\n", b"truncated\xc3"],
                         ids=["oversized-line", "invalid-utf8", "split-final-utf8"])
def test_parser_loss_never_means_clean(data):
    parser = AssemblyDiagnostics(decode=True)
    for offset in range(0, len(data), 8192):
        parser.observe("stderr", data[offset:offset+8192])
    finish(parser, stderr=data)
    assert not parser.complete and parser.input_health()["status"] == "unknown"


def test_oversized_line_does_not_hide_later_degradation_or_invent_fragments():
    lines = []
    parser = AssemblyDiagnostics(decode=True, progress=lines.append, limit=64)
    data = b"x" * 100 + b"\n[h264 @ 0x1] corrupt slice\n"
    parser.observe("stderr", data)
    finish(parser, stderr=data)
    assert not parser.complete and parser.input_health()["status"] == "degraded"
    assert lines == ["ffmpeg: [h264 @ 0x1] corrupt slice"]


def test_missing_eof_and_bypassed_bytes_are_explicit():
    parser = AssemblyDiagnostics(decode=True)
    parser.observe("stderr", b"first\n")
    finish(parser, stderr=b"first\nunobserved", status=("complete", "incomplete"))
    assert not parser.complete and len(parser.problems) == 2
    assert parser.input_health()["status"] == "unknown"


def test_probe_document_overflow_is_explicit_and_memory_bounded():
    parser = AssemblyDiagnostics(probe=True, limit=10)
    parser.observe("stdout", b"x" * 20)
    finish(parser, stdout=b"x" * 20)
    assert bytes(parser.stdout) == b"x" * 10 and not parser.complete


def test_callback_failure_is_not_replayed_on_finish():
    calls = []
    def observer(line):
        calls.append(line)
        raise RuntimeError("observer")
    parser = AssemblyDiagnostics(decode=True, progress=observer)
    with pytest.raises(RuntimeError):
        parser.observe("stderr", b"warning\n")
    finish(parser, stderr=b"warning\n")
    assert len(calls) == 1 and not parser.complete
