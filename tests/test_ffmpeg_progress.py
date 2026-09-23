"""Progress notices stay useful without treating optional SEI as corruption."""

from tikrec.ffmpeg_progress import FfmpegProgressReporter


def test_late_sei_is_reported_once_while_time_progress_continues():
    messages = []
    reporter = FfmpegProgressReporter(messages.append)
    reporter.report("[h264 @ 0x1] Late SEI is not implemented.\n")
    reporter.report("[h264 @ 0x2] Late SEI is not implemented.\nout_time=00:00:02.0\n")
    assert len(messages) == 2
    assert messages[-1] == "encoding progress: 00:00:02.0"
