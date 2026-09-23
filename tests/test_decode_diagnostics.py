"""Fixed, bounded FFmpeg decoder classification without raw log persistence."""

from tikrec.decode_diagnostics import (DecodeDiagnostics, classify_decoder_line,
                                       input_decode_health, safe_input_decode_health)


def test_real_h264_errors_are_bounded_fixed_codes():
    collector = DecodeDiagnostics()
    for _ in range(10002):
        collector.observe("[h264 @ 0x123] error while decoding MB 0 3, bytestream -14")
    collector.observe("[h264 @ 0x123] Reference 3 >= 2")
    value = collector.result()
    assert value == {"status": "degraded", "diagnostic_count": 10000,
                     "diagnostic_codes": ["h264_macroblock", "h264_reference"],
                     "count_capped": True}
    assert "0x123" not in str(value)


def test_late_sei_and_unrelated_warnings_do_not_degrade():
    collector = DecodeDiagnostics()
    collector.observe("[h264 @ 0x1] Late SEI is not implemented. Update FFmpeg.")
    collector.observe("[h264 @ 0x1] If you want to help, upload a sample.")
    collector.observe("https://cdn.example/live.flv?token=secret")
    assert collector.result() == input_decode_health("clean")
    assert classify_decoder_line("[h264 @ 0x1] left block unavailable for requested intra mode") == "h264_intra_prediction"


def test_untrusted_evidence_is_not_exposed():
    hostile = {"status": "degraded", "diagnostic_count": 1,
               "diagnostic_codes": ["https://cdn.example/?token=secret"],
               "count_capped": False}
    assert safe_input_decode_health(hostile) == input_decode_health("unknown")
