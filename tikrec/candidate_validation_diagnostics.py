"""Complete validation diagnostics and bounded streaming packet DTS semantics."""

import codecs
import json

from .assembly_diagnostics import AssemblyDiagnostics
from .part_validation import verify_packet_dts
from .session_journal_types import require


class ValidationDiagnostics(AssemblyDiagnostics):
    """Keep EOF/accounting, fail on any probe stderr, and parse packets incrementally."""

    def __init__(self, index):
        super().__init__(probe=index == 0)
        self.index, self.packet_count = index, 0
        self.stderr_tail = bytearray()
        self.packet_decoder = codecs.getincrementaldecoder("utf-8")("strict")
        self.packet_line, self.previous, self.packet_problems, self.packet_warnings = "", {}, [], []
        self.positions = {}

    def observe(self, name, chunk):
        """Account every byte before parsing; oversized/malformed evidence stays failed."""
        super().observe(name, chunk)
        if name == "stderr":
            self.stderr_tail.extend(chunk)
            del self.stderr_tail[:-2048]
        if self.index == 2 and name == "stdout":
            self._packets(self.packet_decoder.decode(chunk))

    def _packets(self, text):
        self.packet_line += text
        require(len(self.packet_line) <= 65536, "packet framing exceeded bounded size")
        while "\n" in self.packet_line:
            line, self.packet_line = self.packet_line.split("\n", 1)
            self._packet(line.strip())

    def _packet(self, line):
        if not line:
            return
        try:
            values = dict(item.split("=", 1) for item in line.split("|") if "=" in item)
            packet = {"stream_index": int(values["stream_index"]), "dts": int(values["dts"])}
            stream = packet["stream_index"]
            require(stream in self.previous or len(self.previous) < 64, "too many packet streams")
            pair = ([self.previous[stream]] if stream in self.previous else []) + [packet]
            position = self.positions.get(stream, 0) + 1
            # The shared checker sees a pair; restore the full per-stream packet
            # position so its warning remains identical to whole-document checks.
            self.packet_warnings.extend(warning.replace(f"stream {stream} packet 2 ",
                f"stream {stream} packet {position} ", 1)
                for warning in verify_packet_dts(json.dumps({"packets": pair})))
            self.positions[stream] = position
            self.previous[stream] = packet
            self.packet_count += 1
        except (KeyError, TypeError, ValueError) as error:
            self.packet_problems.append(str(error)[:1024])
        require(len(self.packet_problems) + len(self.packet_warnings) <= 32,
                "packet findings exceeded bounded evidence size")

    def finish(self, evidence):
        """Check final packet tail and inherited complete diagnostic EOF/accounting."""
        if self.index == 2:
            self._packets(self.packet_decoder.decode(b"", final=True))
            self._packet(self.packet_line.strip())
            self.packet_line = ""
            if not self.packet_count:
                self.packet_problems.append("candidate contains no valid packets")
        super().finish(evidence)
        if self.problems or self.failures:
            raise (self.problems + self.failures)[0]
        require(self.complete and not self.failures, "validation diagnostics incomplete")

    def stderr_text(self, evidence):
        """Preserve nonempty diagnostics beyond the native prefix as a semantic failure."""
        if not self.seen[1]:
            return ""
        prefix = evidence.stderr[:2048].decode("utf-8", errors="replace")
        tail = bytes(self.stderr_tail).decode("utf-8", errors="replace")
        return prefix + ("\n[diagnostic tail]\n" + tail if evidence.truncated[1] else "") or "FFprobe emitted diagnostics"
