from __future__ import annotations

from io import StringIO
from pathlib import Path
import unittest

from tikrec.progress import LiveProgress


class LiveProgressTests(unittest.TestCase):
    def test_tty_heartbeat_stays_on_the_bottom_line_between_events(self) -> None:
        stdout = StringIO()
        now = [0.0]
        progress = LiveProgress(stdout, clock=lambda: now[0], is_tty=True)

        progress.event("resolving room")
        progress.heartbeat(Path("part-0001.flv"), 142_300_000)
        now[0] = 2.0
        progress.heartbeat(Path("part-0001.flv"), 142_300_000)
        progress.event("room ended")

        self.assertEqual(stdout.getvalue(),
            "resolving room\n"
            "\r\x1b[2K00:00:00  part-0001.flv  142.3 MB"
            "\r\x1b[2Kroom ended\n",
        )

    def test_redirected_output_uses_periodic_complete_lines(self) -> None:
        stdout = StringIO()
        now = [0.0]
        progress = LiveProgress(stdout, clock=lambda: now[0], is_tty=False)

        progress.heartbeat(Path("part-0001.flv"), 1_000_000)
        now[0] = 59.0
        progress.heartbeat(Path("part-0001.flv"), 2_000_000)
        now[0] = 60.0
        progress.heartbeat(Path("part-0001.flv"), 3_000_000)

        self.assertEqual(stdout.getvalue().splitlines(), [
            "00:00:00  part-0001.flv  1.0 MB",
            "00:01:00  part-0001.flv  3.0 MB",
        ])


if __name__ == "__main__":
    unittest.main()
