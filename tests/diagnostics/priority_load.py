"""Bounded test-owned CPU contention and synthetic responsiveness probe."""

import argparse
import hashlib
import json
from pathlib import Path
import time


def run_load(mode, stop, result, seconds):
    """Stop at the test marker or deadline and persist fixed-work probe samples."""
    started = time.perf_counter()
    deadline = started + seconds
    samples = []
    tick = started
    while time.perf_counter() < deadline and not stop.exists():
        if mode == "cpu":
            # One sequential worker consumes at most one logical CPU at a time.
            hashlib.pbkdf2_hmac("sha256", b"test-owned-contention", b"fixed", 30_000)
            continue
        tick += 1 / 60
        time.sleep(max(0, tick - time.perf_counter()))
        wake = time.perf_counter()
        # Fixed work, not adaptive work: the same iterations run at both priorities.
        value = 0
        for i in range(20_000):
            value = (value + i * 17) % 1_000_003
        ended = time.perf_counter()
        samples.append({"scheduled": tick, "wake": wake, "end": ended, "check": value})
        if ended - tick > 1 / 60:
            # Do not create a backlog that turns scheduler delay into an endless busy loop.
            tick = ended
    if result is not None:
        result.write_text(json.dumps(samples) + "\n", encoding="utf-8")


def main():
    """Run only an explicitly bounded disposable workload."""
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("cpu", "probe"))
    parser.add_argument("--stop", type=Path, required=True)
    parser.add_argument("--result", type=Path)
    parser.add_argument("--seconds", type=float, default=65)
    args = parser.parse_args()
    if not 0 < args.seconds <= 90:
        parser.error("deadline must be 1–90 seconds")
    run_load(args.mode, args.stop, args.result, args.seconds)


if __name__ == "__main__":
    main()
