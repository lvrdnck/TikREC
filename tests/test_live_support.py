"""The helper extraction preserves reconnect counters and diagnostic formatting."""

import unittest

from tikrec.live_support import _next_failure_counts, _safe_reason, _validate_limits


class LiveSupportTests(unittest.TestCase):
    def test_media_resets_both_streaks(self):
        self.assertEqual(_next_failure_counts(True, 2, 2), (0, 0))
        self.assertEqual(_next_failure_counts(False, 2, 2), (3, 2))

    def test_signed_urls_remain_redacted_from_progress(self):
        self.assertEqual(_safe_reason(OSError("failed https://cdn.test/live.flv?secret=x")),
                         "failed [URL redacted]")

    def test_policy_limit_validation_remains_unchanged(self):
        _validate_limits(3, 3, 1.0, 3, 5.0)
        with self.assertRaises(ValueError):
            _validate_limits(0, 3, 1.0, 3, 5.0)


if __name__ == "__main__":
    unittest.main()
