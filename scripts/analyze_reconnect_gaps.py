#!/usr/bin/env python3
"""Render TikREC reconnect-gap evidence without changing recording artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TextIO

# Make the checkout-local package available when this file is invoked directly.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tikrec.gap_analysis import (
    COMPONENTS, analyze_records, boundary_events, gap_as_dict, read_connection_log, summarize_gaps,
)


def analyze_paths(paths: Sequence[Path], *, as_json: bool = False, stdout: TextIO = sys.stdout) -> int:
    """Analyze one or more connection logs and write deterministic diagnostics."""
    reports = []
    for path in paths:
        records = read_connection_log(path)
        gaps = analyze_records(records)
        ordinary = tuple(gap for gap in gaps if gap.classification == "ordinary")
        reports.append({
            "path": str(path),
            "reconnects": [gap_as_dict(gap) for gap in gaps],
            "ordinary_reconnect_count": len(ordinary),
            "observed_boundaries": boundary_events(records),
            "ordinary_summary": {
                name: vars(summary) for name, summary in summarize_gaps(gaps).items()
            },
        })
    if as_json:
        print(json.dumps(reports, indent=2, sort_keys=True), file=stdout)
    else:
        for report in reports:
            _render_report(report, stdout)
    return 0


def _render_report(report: dict, stdout: TextIO) -> None:
    print(f"Connection log: {report['path']}", file=stdout)
    print(f"Reconnects: {len(report['reconnects'])}; ordinary: {report['ordinary_reconnect_count']}",
          file=stdout)
    if report["observed_boundaries"]:
        print(f"Observed boundaries: {', '.join(report['observed_boundaries'])}", file=stdout)
    for gap in report["reconnects"]:
        print(f"  {gap['previous_connection']} -> {gap['current_connection']} "
              f"[{gap['classification']}]", file=stdout)
        for component in COMPONENTS:
            value = gap[component]
            rendered = "unknown" if value is None else f"{value:.3f}s"
            print(f"    {component}: {rendered}", file=stdout)
        if gap["intervening_attempts"]:
            attempts = ", ".join(
                f"{item['connection']}:{item['outcome'] or 'unknown'}"
                for item in gap["intervening_attempts"]
            )
            print(f"    intervening_attempts: {attempts}", file=stdout)
        if gap["unrecorded_attempt_count"]:
            print(f"    unrecorded_attempt_count: {gap['unrecorded_attempt_count']}", file=stdout)
        if gap["boundary_events"]:
            print(f"    boundary_events: {', '.join(gap['boundary_events'])}", file=stdout)
    if report["ordinary_reconnect_count"]:
        print("  Ordinary reconnect summary (median [range], seconds):", file=stdout)
        for component in COMPONENTS:
            summary = report["ordinary_summary"][component]
            if summary["count"]:
                print(f"    {component}: {summary['median_seconds']:.3f} "
                      f"[{summary['minimum_seconds']:.3f}, {summary['maximum_seconds']:.3f}] "
                      f"n={summary['count']}", file=stdout)
            else:
                print(f"    {component}: unknown (n=0)", file=stdout)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the read-only reconnect-gap diagnostic."""
    parser = argparse.ArgumentParser(description="Analyze TikREC connections.jsonl gap evidence.")
    parser.add_argument("connection_logs", metavar="CONNECTIONS_JSONL", nargs="+", type=Path)
    parser.add_argument("--json", action="store_true", help="emit structured JSON")
    arguments = parser.parse_args(argv)
    return analyze_paths(arguments.connection_logs, as_json=arguments.json)


if __name__ == "__main__":
    raise SystemExit(main())
