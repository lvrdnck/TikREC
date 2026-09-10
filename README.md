# TikREC

A command-line tool for recording public TikTok LIVE streams to disk.

Point it at a LIVE page, it records until the stream ends or you stop it,
reconnecting if the connection drops, and you get one MP4 out.

## Usage

    tikrec live <tiktok-live-page-url> --output FILE
    tikrec record <direct-flv-url> --output FILE
    tikrec resolve <tiktok-live-page-url>

`live` records a public LIVE page and reconnects across dropped
connections. `record` takes a direct FLV URL and is source-agnostic.
`resolve` prints the current direct FLV URL for a live page.

For `live`, the first Ctrl-C stops capture, finalizes retained parts, and exits
130 to show that recording ended early. A second Ctrl-C during finalization
stops FFmpeg; retained parts always remain available.

## Requirements

- Python 3.11+
- ffmpeg and ffprobe on PATH

Install with `pip install -e .`

## How it works

The stream is written as numbered FLV parts, each independently
decodable. A new part starts when the video codec configuration changes
or when a dropped connection is re-established. Parts are then stitched
into a single MP4 — losslessly when the configurations match, re-encoded
when they don't.

Each recording writes `connections.jsonl` alongside the parts: one line
per connection, with wall-clock timings, the gap before it, and per-part
timestamp diagnostics.

## Validating a recording

    python3 scripts/validate_parts.py path/to/recording.parts

Checks every retained part decodes and has monotonic stored timestamps.
Note that `ffmpeg -f null -` is *not* a valid check here — see the
validation notes in SPEC.md for why.

## Scope

Public LIVE streams only. No authenticated or gated access, no private
API signing, no waiting for a stream to start, no monitoring anyone.
See SPEC.md.

## Design

[SPEC.md](SPEC.md) — architecture, module responsibilities, validation
notes and the reasoning behind past fixes.
[AGENTS.md](AGENTS.md) — working rules.
