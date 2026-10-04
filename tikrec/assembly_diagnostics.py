"""Bounded chunk framing for complete FFmpeg diagnostics and small probe replies."""

import codecs

from .decode_diagnostics import DecodeDiagnostics, input_decode_health
from .ffmpeg_progress import FfmpegProgressReporter


class AssemblyDiagnostics:
    """Observe all collected bytes independently of the process's retained prefix.

    Oversized lines/probe documents and invalid UTF-8 explicitly lose diagnostic
    completeness. Nothing discarded by the parser may establish clean input.
    """

    def __init__(self, *, decode=False, progress=None, probe=False, limit=65536):
        self.decoder = codecs.getincrementaldecoder("utf-8")("strict")
        self.health = DecodeDiagnostics() if decode else None
        self.reporter = FfmpegProgressReporter(progress)
        self.probe, self.limit = probe, limit
        self.stdout, self.line = bytearray(), []
        self.seen, self.discarding, self.finished = [0, 0], False, False
        self.problems, self.failures, self.complete = [], [], False

    def _problem(self, message):
        if len(self.problems) < 8:
            self.problems.append(ValueError(message))

    def observe(self, name, chunk):
        """Consume bounded native chunks, preserving split UTF-8 and logical lines."""
        self.seen[0 if name == "stdout" else 1] += len(chunk)
        if name == "stdout":
            if self.probe:
                room = self.limit - len(self.stdout)
                self.stdout.extend(chunk[:room])
                if len(chunk) > room:
                    self._problem("probe output exceeded bounded document size")
            return
        try:
            text = self.decoder.decode(chunk)
        except UnicodeDecodeError:
            self._problem("diagnostic UTF-8 could not be decoded completely")
            self.decoder.reset()
            text = chunk.decode("utf-8", errors="replace")
        self._frame(text)

    def _frame(self, text):
        # Native chunks are at most 8 KiB. A logical line can span many chunks;
        # discard its entire remainder after overflow rather than inventing lines.
        for character in text:
            if character in "\r\n":
                line = "".join(self.line) if not self.discarding else ""
                self.line, self.discarding = [], False
                if line:
                    self._report(line)
            elif not self.discarding:
                if len(self.line) < self.limit:
                    self.line.append(character)
                else:
                    self._problem("diagnostic line exceeded bounded framing size")
                    self.line, self.discarding = [], True

    def _report(self, line):
        # This installed FFmpeg can return zero for an occupied -n output.
        # Preserve explicit tool failure separately from input-decode degradation.
        if line.startswith(("Error opening output file", "Error opening input file", "Conversion failed!")):
            if len(self.failures) < 8:
                self.failures.append(RuntimeError(f"FFmpeg reported execution failure: {line[:1024]}"))
        if self.health is not None:
            self.health.observe(line)
        try:
            self.reporter.report(line)
        except BaseException:
            self._problem("diagnostic observer failed; delivery is incomplete")
            raise

    def finish(self, evidence):
        """Reconcile EOF and accounting, including the last unterminated line."""
        if self.finished:
            return
        self.finished = True
        if evidence.stream_status != ("complete", "complete"):
            self._problem("native diagnostic EOF is incomplete")
        collected = (len(evidence.stdout) + evidence.truncated[0],
                     len(evidence.stderr) + evidence.truncated[1])
        if tuple(self.seen) != collected:
            self._problem("collected diagnostics bypassed streaming observation")
        try:
            self._frame(self.decoder.decode(b"", final=True))
        except UnicodeDecodeError:
            self._problem("final diagnostic UTF-8 tail is incomplete")
        line = "".join(self.line) if not self.discarding else ""
        self.line = []
        if line:
            self._report(line)
        self.complete = not self.problems

    def input_health(self):
        """Keep degraded evidence; incomplete absence of errors cannot mean clean."""
        if self.health is None:
            return input_decode_health("not_checked")
        result = self.health.result()
        return input_decode_health("unknown") if not self.complete and result["status"] == "clean" else result
