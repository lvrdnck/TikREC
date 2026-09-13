# TikREC

A command-line recorder and small remote-control service for public TikTok LIVE streams.

Point it at a LIVE page, it records until the stream ends or you stop it,
reconnecting if the connection drops, and you get one MP4 out.

## Usage

    tikrec live <tiktok-live-page-url> --output FILE [--raw-copy DIR]
    tikrec record <direct-flv-url> --output FILE [--raw-copy DIR]
    tikrec resolve <tiktok-live-page-url>
    tikrec finalize PARTS_DIRECTORY --output FILE
    tikrec validate TARGET [--deep] [--json]
    tikrec serve [--host IP] [--port PORT] [--token-file FILE]
    tikrec remote health --server URL [--token-file FILE]
    tikrec remote status --server URL [--token-file FILE]
    tikrec remote start --server URL PUBLIC_LIVE_URL --output ABSOLUTE_PC_MP4_PATH [--token-file FILE]
    tikrec remote stop --server URL [--token-file FILE]
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

## Remote recording on an always-on PC

The intended setup is Mac -> Tailscale -> main-pc -> TikREC service -> recording
files on main-pc. Run `tikrec serve` independently through Windows Task Scheduler
so capture continues when SSH/VS Code closes, the Mac lid shuts, or the Mac loses
network access. Launching `serve` directly inside SSH still ties the service to
that shell; Task Scheduler owns the persistent process.

The default is `127.0.0.1:8765`. Remote binding requires an explicit IP and a
bearer secret from `--token-file FILE` or `TIKREC_TOKEN`. A token file overrides
the environment. Use the same secret on the Mac. No virtualenv activation is
needed when invoking the installed executable by absolute path:

```powershell
C:\Users\Leandro\dev\TikREC\.venv\Scripts\tikrec.exe serve --host 100.x.y.z --token-file C:\Users\Leandro\TikREC-secrets\token.txt
```

On the Mac (replace the address and username):

```sh
tikrec remote health --server http://main-pc:8765 --token-file ~/.config/tikrec/token.txt
tikrec remote start --server http://main-pc:8765 https://www.tiktok.com/@username/live --output 'C:\Users\Leandro\Videos\name.mp4' --token-file ~/.config/tikrec/token.txt
tikrec remote status --server http://main-pc:8765 --token-file ~/.config/tikrec/token.txt
tikrec remote stop --server http://main-pc:8765 --token-file ~/.config/tikrec/token.txt
```

One recording may be active. Start and stop acknowledge requests immediately;
poll status until `completed` or `failed` to see the final result. Remote stop
closes/retains the active FLV part, finalizes output, and writes `session.json`.
It never sends a kill signal to FFmpeg. A stopped job reports `completed` with
`interrupted: true`; `final_output_path` identifies an actual finalized output.
Capture/finalizer failure preserves retained parts for `tikrec finalize`.

See [SERVICE.md](SERVICE.md) for the API contract, secret handling, Windows Task
Scheduler settings, and deployment verification. v0.4 keeps only the current or
latest job in memory; service-crash/reboot reconciliation and automatic resume
remain v0.5 work. There is no Web UI or media-download endpoint.

v0.5 implementation includes offline-tested durable job-state storage and
structured public room resolution. The numeric room ID identifies the LIVE;
username identifies the account, and signed CDN URLs are temporary transport
locations. Missing or ambiguous room identity will prevent automatic resume in
the later reconciliation layer. Storage/recovery is not yet connected to
`serve`; the version remains v0.4.0. See [SERVICE.md](SERVICE.md) for the boundary.

Internal explicit resume APIs now continue a supported interrupted session into
new numbered parts. They preserve old FLV files and the session ID, give the new
connection fresh codec/timestamp state, and can finalize old plus new parts.
Gaps, abandoned partials, conflicting paths, or existing outputs block resume.
There is no resume CLI/remote endpoint or automatic service recovery yet.

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
[ROADMAP.md](ROADMAP.md) — workflow-driven direction for future releases.
[SERVICE.md](SERVICE.md) — remote API and Windows Task Scheduler deployment.
[SESSION_MANIFEST.md](SESSION_MANIFEST.md) — `session.json` schema and lifecycle.
[AGENTS.md](AGENTS.md) — working rules.
