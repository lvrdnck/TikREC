# TikREC

A command-line tool for recording public TikTok LIVE streams to disk.

Point it at a LIVE page, it records until the stream ends or you stop it,
reconnecting if the connection drops, and you get one MP4 out.

## Usage

    tikrec live <tiktok-live-page-url> --output FILE [--raw-copy DIR]
    tikrec record <direct-flv-url> --output FILE [--raw-copy DIR]
    tikrec resolve <tiktok-live-page-url>
    tikrec finalize PARTS_DIRECTORY --output FILE

`live` records a public LIVE page and reconnects across dropped
connections. After media has been recorded, TikREC accepts that a room ended
only after three consecutive non-live responses spaced five seconds apart. A
room that is offline on the first resolve still fails immediately. `record`
takes a direct FLV URL and is source-agnostic.
`resolve` prints the current direct FLV URL for a live page.
`finalize` stitches retained `part-*.flv` files after an interrupted or
otherwise stopped recording. It preserves those parts and refuses to overwrite
an existing output file.

For `live`, the first Ctrl-C stops capture, finalizes retained parts, and exits
130 to show that recording ended early. A second Ctrl-C during finalization
stops FFmpeg; retained parts always remain available.

`--raw-copy DIR` optionally saves the exact bytes received from every source
connection before FLV parsing, as `connection-0001.raw`,
`connection-0002.raw`, and so on. `connections.jsonl` identifies the raw file
for each connection. A raw-copy error only emits a warning; recording
continues. Raw copies roughly double the recording's disk use.

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

Each live recording, and each direct recording using `--raw-copy`, writes
`connections.jsonl` alongside the parts. Connection records contain wall-clock
timings, the preceding gap, per-part timestamp diagnostics, and the optional
raw-copy filename. Live recordings also contain `room_status` event records
during end confirmation. Each event has a timestamp, the raw TikTok room-status
value, and whether that response reached the confirmation threshold. A live
response that cancels confirmation is recorded too.

## Validating a recording

    python3 scripts/validate_parts.py path/to/recording.parts

Checks every retained part decodes. Missing, malformed, or duplicate stored
DTS fails validation; a decreasing DTS is reported as a warning with its
position and magnitude.
Note that `ffmpeg -f null -` is *not* a valid check here — see the
validation notes in SPEC.md for why.

## Scope

Public LIVE streams only. No authenticated or gated access, no private
API signing, no waiting for a stream to start, no monitoring anyone.
See SPEC.md.

## Design

[SPEC.md](SPEC.md) — architecture, module responsibilities, validation
notes and the reasoning behind past fixes.
[ROADMAP.md](ROADMAP.md) — dependency-ordered direction for future releases.
[AGENTS.md](AGENTS.md) — working rules.
