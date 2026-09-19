# TikREC

A command-line recorder and small remote-control service for public TikTok LIVE streams.

Point it at a LIVE page, it records until the stream ends or you stop it,
reconnecting if the connection drops, and you get one MP4 out.

This reliability-first implementation is the foundation of a broader future
livestream recording platform. Creator automation, a library, playback, and web
workflows are product direction, but they are not commands or service features today.

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
for each connection. A matching `connection-NNNN.arrivals.jsonl` sidecar records
the local HTTP-read time and byte range for each returned chunk, and the
connection record names it in `raw_arrivals`. These timings diagnose where a
stall became visible to TikREC; buffering means they are not TCP/TLS packet
boundaries or exact network/server arrival times. Raw-copy and arrival-log errors
only emit warnings; recording continues. Raw copies roughly double the
recording's disk use, with additional small arrival-log overhead. See
[CONNECTION_LOG.md](CONNECTION_LOG.md) for the evidence contract.

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
Scheduler settings, startup recovery, and deployment verification. There is no
Web UI or media-download endpoint in the current service. Package version v0.5.0
is the release candidate being prepared; v0.4.0 remains the current tagged and
published GitHub Release until the separately authorized v0.5.0 tag and release.

The service now persists its latest explicitly started job. After an unexpected
process death and Task Scheduler restart, it checks that job against retained
parts/session evidence before accepting new recordings. Automatic resume applies
only to the explicitly-started prior LIVE, proven by the same canonical room ID.
It preserves the job/session ID and old FLV files, increments resume_count, and
starts a fresh connection and the next numbered part. Normal reconnects continue;
a later different room is never connected by a resumed recording.

Confirmed offline or a different LIVE ends the prior session and safely finalizes
its retained parts when output is missing. A prior stop request or finalizing job
skips TikTok resolution and retries only safe finalization. Completed jobs do not
restart; an idle maintenance restart stays idle. This never means monitor this
username and record the next LIVE.

During an established LIVE or startup reconciliation, temporary DNS/internet,
timeout, connection-reset, and HTTP 408/425/429/5xx failures enter patient recovery.
Waits are 1, 2, 5, 10, 10, then 30 seconds, capped at 30 seconds, for up to 15
minutes from the first transient failure. Retry-After can increase a wait to that
cap. Status reports `state=recovering_network`, `recovery_state=recovery_wait`,
attempt/countdown/elapsed fields; health/status stay readable and starts return
409. Stop or service shutdown wakes retry waits and finalizes retained media.
Same-room recovery continues into fresh parts; offline/different-room evidence
ends the prior LIVE. Healthy reconnect timing and offline confirmation stay unchanged.

Exhaustion reports `failed`, `recovery_reason=outage_timeout`, retains all parts,
and leaves output unfinalized because room end is unproven. The service permits a
new explicit job; restart never relaunches an exhausted job. A crash during an
unfinished outage preserves non-terminal intent and starts a fresh recovery window
on reconciliation. Malformed identity/storage also blocks starts with a fixed safe error.
A nonempty FFmpeg partial is automatically preserved under a collision-safe
session evidence name and all retained parts are re-finalized only when durable
job and manifest state prove finalization was running. Unproven, empty,
nonregular, colliding, or output-coexisting partials need manual assessment.
Existing output is preserved and accepted only with matching committed completion
and bounded media evidence; ambiguous output is never replaced. Real abrupt-
restart, temporary-outage, graceful-stop/finalization, retained-session, and deep-
output deployment validation have passed on preserved evidence.

A hard service stop can leave the active writer file named
`.part-NNNN.flv.partial`. Startup recovery accepts only the canonical next part
proven by matching durable recording intent, manifest identity/lifecycle, paths,
counts, artifact inventory, output absence, FLV structure, and decoder/DTS checks.
It preserves the exact original under a session/index evidence name, separately
copies either the complete file or its last parser-proven complete-tag prefix,
then resumes with a fresh connection and next part. Every unowned, conflicting,
malformed, empty, colliding, or nonregular partial remains untouched and blocks.
Issue #14's repeat real deployment validation passed; operators must not rename,
truncate, or delete crash evidence.

State lives at %LOCALAPPDATA%\TikREC\job.json on Windows and
${XDG_STATE_HOME:-~/.local/state}/TikREC/job.json elsewhere, independent of the
working directory. Use the same task account and one service instance. Existing
v0.4 recordings with no durable job are not inferred from directories or usernames.
Internal generic resume APIs remain available; no resume CLI/remote endpoint is added.

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
raw-copy and raw-arrival filenames. Live recordings also contain `room_status` event records
during end confirmation. Each event has a timestamp, the raw TikTok room-status
value, and whether that response reached the confirmation threshold. A live
response that cancels confirmation is recorded too. Coalesced `network_recovery`
boundaries summarize outage entry and outcome without logging every retry wait.

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

**Today:** TikREC records one manually supplied public LIVE and exposes the
commands and four service endpoints documented above. It does not currently
store creator lists, wait for future LIVEs, monitor configured handles, record
multiple creators, authenticate to TikTok, or provide a library/Web UI/playback.

**Future product:** explicitly configured public-creator monitoring and automatic
recording are planned after the reliability foundation. Library/history/playback,
a web interface, and other predecessor capabilities remain in long-term planning;
their old implementation and architecture are not authoritative.

**Permanent boundary:** TikREC will not bypass authentication, CAPTCHA,
entitlements, access controls, or private request signing, and will not support
covert surveillance or destructive handling of user recordings/evidence. A
separately designed future authenticated mode may use authorization explicitly
supplied by the user while respecting platform controls. See SPEC.md and
ROADMAP.md.

## Design

[SPEC.md](SPEC.md) — architecture, module responsibilities, validation
notes and the reasoning behind past fixes.
[ROADMAP.md](ROADMAP.md) — workflow-driven direction for future releases.
[SERVICE.md](SERVICE.md) — remote API and Windows Task Scheduler deployment.
[SESSION_MANIFEST.md](SESSION_MANIFEST.md) — `session.json` schema and lifecycle.
[PROJECT_STATE.md](PROJECT_STATE.md) — concise current development handoff.
[AGENTS.md](AGENTS.md) — working rules.
