# TikREC

A command-line tool for recording public TikTok LIVE streams to disk.

Point it at a LIVE page, it records until the stream ends or you stop it,
reconnecting if the connection drops, and you get one MP4 out.

## Usage

    tikrec live <tiktok-live-page-url> --output FILE [--raw-copy DIR]
    tikrec record <direct-flv-url> --output FILE [--raw-copy DIR]
    tikrec resolve <tiktok-live-page-url>
    tikrec finalize PARTS_DIRECTORY --output FILE
    tikrec validate TARGET [--deep] [--json]
    tikrec --version

`live` records a public LIVE page and reconnects across dropped
connections. After media has been recorded, TikREC accepts that a room ended
only after three consecutive non-live responses spaced five seconds apart. A
room that is offline on the first resolve still fails immediately. `record`
takes a direct FLV URL and is source-agnostic.
`resolve` prints the current direct FLV URL for a live page.
`finalize` stitches retained `part-*.flv` files after an interrupted or
otherwise stopped recording. It preserves those parts and refuses to overwrite
an existing output file. `validate` inspects an output file, parts directory,
or session without changing it.

For `live`, the first Ctrl-C stops capture, clearly announces that finalization
has begun, finalizes retained parts, and exits 130 to show that recording ended
early. Matching parts are stream-copied; differing video configurations require
a re-encode that may take several minutes or longer. During encoding TikREC
reports output time instead of forwarding FFmpeg's complete diagnostic stream.
A second Ctrl-C during finalization stops FFmpeg; retained parts always remain
available.

`--raw-copy DIR` optionally saves the exact bytes received from every source
connection before FLV parsing, as `connection-0001.raw`,
`connection-0002.raw`, and so on. `connections.jsonl` identifies the raw file
for each connection. A raw-copy error only emits a warning; recording
continues. Raw copies roughly double the recording's disk use.

An open media connection that delivers no bytes for 30 seconds is treated as a
stall. Live capture records a `stalled` connection outcome and reconnects under
the same bounded transient-failure policy used for other connection errors.

## Requirements

- Python 3.11+
- ffmpeg and ffprobe on PATH

Install with `pip install -e .`

TikREC writes to the path supplied with `--output`; relative paths start from
the current directory. Prefer a dedicated recording directory outside a source
checkout. While developing TikREC, `runs/` is the repository's ignored local
recording directory:

    mkdir -p runs
    tikrec live <tiktok-live-page-url> --output runs/recording.mp4

## How it works

The stream is written as numbered FLV parts intended to be independently
decodable. A known unresolved exception is a source timestamp replay: retained
replay intervals can contain malformed H.264 that fails decoding even in a
freshly initialized decoder. TikREC preserves that evidence and warns that the
affected part may not validate. A new part starts when the video codec
configuration changes or when a dropped connection is re-established. Parts
are then stitched into a single MP4 — losslessly when the configurations match,
re-encoded when they don't.

Each live recording, and each direct recording using `--raw-copy`, writes
`connections.jsonl` alongside the parts. Connection records contain wall-clock
timings, the preceding gap, per-part timestamp diagnostics, and the optional
raw-copy filename. Live recordings also contain `room_status` event records
during end confirmation. Each event has a timestamp, the raw TikTok room-status
value, and whether that response reached the confirmation threshold. A live
response that cancels confirmation is recorded too.

Every recording session also writes `session.json` alongside the parts. It is
an atomically updated, high-level summary of the session lifecycle, result,
paths, part and connection counts, interruption/finalization state, and optional
codec and resolution information. It complements the lower-level
`connections.jsonl`; see [SESSION_MANIFEST.md](SESSION_MANIFEST.md) for the
schema and lifecycle.

## Validating a recording

    tikrec validate path/to/recording.mp4
    tikrec validate path/to/recording.mp4 --deep
    tikrec validate path/to/recording.parts
    tikrec validate path/to/recording.parts/session.json --json

For retained parts, validation checks that each file is readable and non-empty,
contains recognizable video, decodes through FFprobe, and has valid stored
packet DTS. Missing, malformed, or duplicate DTS fails validation; a decreasing
DTS is a warning because it is known TikTok source behavior. Missing audio is
also a warning so a valid video-only source is not labeled corrupt.

For a completed output, validation checks readability, FFprobe inspection,
video and optional audio streams, container information, and a positive finite
duration. `--deep` additionally decodes the complete output and can take
significant time and CPU for a long recording. Retained parts always receive
the full decode check, with or without `--deep`. When `session.json` is present
validation also checks the actual part count, declared output, finalization
state, and available codec/resolution metadata. Older parts directories without
a manifest remain supported.

An interrupted, failed, or still-recording session is not corrupt merely
because it is incomplete or has no final MP4. The report presents media
integrity, session completeness, and output availability separately. Validation
is read-only: it never finalizes, repairs, renames, deletes, or rewrites media or
session metadata. It is a structural health check, not exhaustive media
forensics.

Exit 0 means validation passed, exit 1 means one or more checks failed, and
invalid command usage keeps argparse's exit 2. `--json` emits the same result
with stable finding levels and codes. The legacy
`scripts/validate_parts.py` command remains as a compatibility wrapper over the
same validator.

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
[SESSION_MANIFEST.md](SESSION_MANIFEST.md) — `session.json` schema and lifecycle.
[AGENTS.md](AGENTS.md) — working rules.
