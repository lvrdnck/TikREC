#!/usr/bin/env python3
"""Compare established-room resolver latency without changing capture behavior."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TextIO

# Make the checkout-local package available when this file is invoked directly.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tikrec.resolver_benchmark import benchmark_resolution


def render_report(report: dict, *, stdout: TextIO = sys.stdout) -> None:
    """Render safe request timings and equivalence facts without transport URLs."""
    print(f"Saved room ID: {report['saved_room_id']}", file=stdout)
    for pair in report["pairs"]:
        print(f"Sample {pair['sample']} ({' then '.join(pair['order'])})", file=stdout)
        for path in ("bound", "direct"):
            run = pair[path]
            print(
                f"  {path}: {run['outcome']}; total={run['total_seconds']:.3f}s",
                file=stdout,
            )
            for request in run["requests"]:
                result = "ok" if request["succeeded"] else "failed"
                print(
                    f"    {request['stage']}: {request['seconds']:.3f}s ({result})",
                    file=stdout,
                )
        equivalent = pair["equivalence"]
        print(
            "  equivalence: "
            f"comparable={equivalent['comparable']}, "
            f"room={equivalent['room_id_equal']}, "
            f"label={equivalent['rendition_label_equal']}, "
            f"source={equivalent['rendition_source_equal']}, "
            f"transport={equivalent['media_transport_equal']}",
            file=stdout,
        )
    print("Summary:", file=stdout)
    for name, value in report["summary"].items():
        rendered = "unknown" if value is None else (
            str(value) if name.endswith("count") else f"{value:.3f}s"
        )
        print(f"  {name}: {rendered}", file=stdout)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the bounded read-only established-room resolver benchmark."""
    parser = argparse.ArgumentParser(
        description="Compare bound and direct known-room resolver timings read-only."
    )
    parser.add_argument("live_url", metavar="TIKTOK_LIVE_URL")
    parser.add_argument("room_id", metavar="SAVED_ROOM_ID")
    parser.add_argument("--samples", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=15)
    parser.add_argument("--json", action="store_true", help="emit safe structured JSON")
    arguments = parser.parse_args(argv)
    report = benchmark_resolution(
        arguments.live_url,
        arguments.room_id,
        samples=arguments.samples,
        timeout=arguments.timeout,
    )
    if arguments.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        render_report(report)
    return 0 if report["summary"]["comparable_sample_count"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
