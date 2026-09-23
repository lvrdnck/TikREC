"""Reduce FFmpeg progress and warning lines for the CLI."""

from collections.abc import Callable


class FfmpegProgressReporter:
    """Report encoding progress without repeating optional metadata warnings."""

    _PROGRESS_KEYS = {
        "bitrate", "drop_frames", "dup_frames", "fps", "frame", "out_time_ms",
        "out_time_us", "progress", "speed", "total_size",
    }

    def __init__(self, progress: Callable[[str], None] | None) -> None:
        self._progress = progress
        self._late_sei_reported = False

    def report(self, stderr: str | None) -> None:
        """Report time progress and diagnostics without repeated metadata warnings."""
        if self._progress is None or not stderr:
            return
        for line in stderr.splitlines():
            if not line:
                continue
            if "Late SEI is not implemented" in line:
                if not self._late_sei_reported:
                    self._progress(
                        "ffmpeg: late H.264 SEI metadata is unsupported; "
                        "repeated warnings suppressed"
                    )
                    self._late_sei_reported = True
                continue
            if self._late_sei_reported and "If you want to help" in line:
                continue
            key, separator, value = line.partition("=")
            if separator and key == "out_time":
                self._progress(f"encoding progress: {value}")
            elif separator and (key in self._PROGRESS_KEYS or key.startswith("stream_")):
                continue
            else:
                self._progress(f"ffmpeg: {line}")
