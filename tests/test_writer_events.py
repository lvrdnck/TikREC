"""Source-clock diagnostics retain backward intervals rather than suppressing them."""

import unittest
from pathlib import Path
from types import SimpleNamespace

from tikrec.writer_events import PartTiming, _observe_timestamp
from tests.test_writer import video


class WriterEventTests(unittest.TestCase):
    def test_old_part_timing_constructor_keeps_facts_optional(self):
        timing = PartTiming(Path("part.flv"), 0, 100, 120, 200)
        self.assertEqual(timing.keyframe_gate_duration, 20)
        self.assertIsNone(timing.nominal_frame_rate)
        self.assertIsNone(timing.width)

    def test_replay_is_observed_until_recovery(self):
        part = SimpleNamespace(final_path=Path("part.flv"), tag_position=0,
                               pending_replays={}, last_observed_timestamps={}, timestamp_replays=[])
        events = []
        for timestamp in (100, 20, 40, 120):
            part.tag_position += 1
            _observe_timestamp(part, video(timestamp, 2), events.append)
        self.assertEqual(len(events), 1)
        self.assertEqual((events[0].position, events[0].magnitude, events[0].replayed_tag_count), (2, 80, 2))
        self.assertTrue(events[0].recovered)


if __name__ == "__main__":
    unittest.main()
